//! wgpu renderer: per-part BLAS + one TLAS (an instance per part, each with its own transform), compute path
//! tracer, a-trous denoiser. The model can be replaced while it runs.
use crate::scene::{FLAG_SEL, GpuPart, Scene};
use bytemuck::{Pod, Zeroable};
use glam::Vec3;
use std::time::Instant;
use wgpu::util::DeviceExt;

/// Where a picture at rest stops. (With the last light denoise it is then as clean as the reference's.)
pub const MAX_SPP: u32 = 1024;
/// The most samples a pixel is given in one frame.
pub const MAX_SPF: u32 = 64;
const STILL_MS: f64 = 12.0;     // the card's time in one frame of a picture at rest
/// a moving frame takes no longer than this (24 fps): see `note_frame`. DESK_FLOOR_FPS: another floor, to
/// see the stepping on a card too fast to need it (a debugging aid)
#[cfg(feature = "dlss")]
fn floor_ms() -> f64 {
    static F: std::sync::OnceLock<f64> = std::sync::OnceLock::new();
    *F.get_or_init(|| 1000.0 / std::env::var("DESK_FLOOR_FPS").ok().and_then(|v| v.parse::<f64>().ok()).filter(|f| *f > 0.0).unwrap_or(24.0))
}
pub const ATROUS_PASSES: usize = 5;
pub const IDENT: [f32; 12] = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0];

/// DLSS ENLARGING THE PICTURE WHILE IT MOVES (the settings window): the picture is traced smaller, by
/// DLSS's own ratio for the mode, and DLSS makes it the window's size. At rest it is traced at its own size
/// as ever, so the picture it settles to is the same. Off: DLSS cleans the picture at its own size (DLAA).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug, Default)]
pub enum Upscale {
    #[default]
    Off,
    Quality,
    Balanced,
    Performance,
    Ultra,
}

impl Upscale {
    pub const ALL: [Upscale; 5] = [Upscale::Off, Upscale::Quality, Upscale::Balanced, Upscale::Performance, Upscale::Ultra];

    pub fn name(self) -> &'static str {
        match self {
            Upscale::Off => "off",
            Upscale::Quality => "quality",
            Upscale::Balanced => "balanced",
            Upscale::Performance => "performance",
            Upscale::Ultra => "ultra",
        }
    }

    pub fn parse(s: &str) -> Option<Upscale> {
        Upscale::ALL.into_iter().find(|u| u.name() == s)
    }

    /// the share of the picture's pixels traced (DLSS's ratios: 1/1.5, 1/1.72, 1/2, 1/3 a side)
    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    fn frac(self) -> f64 {
        [1.0, 0.444, 0.338, 0.25, 0.111][self as usize]
    }

    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    fn up(self) -> Upscale {
        Upscale::ALL[(self as usize + 1).min(4)]
    }

    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    fn down(self) -> Upscale {
        Upscale::ALL[(self as usize).saturating_sub(1)]
    }

    #[cfg(feature = "dlss")]
    fn mode(self) -> Option<dlss_wgpu::DlssPerfQualityMode> {
        use dlss_wgpu::DlssPerfQualityMode as M;
        match self {
            Upscale::Off => None,
            Upscale::Quality => Some(M::Quality),
            Upscale::Balanced => Some(M::Balanced),
            Upscale::Performance => Some(M::Performance),
            Upscale::Ultra => Some(M::UltraPerformance),
        }
    }
}

/// A camera in the CAD frame (Z up): where it is, its right / up / forward, the vertical field of view.
#[derive(Clone, Copy, PartialEq, Debug)]
pub struct Camera {
    pub eye: Vec3,
    pub r: Vec3,
    pub u: Vec3,
    pub f: Vec3,
    pub tan_y: f32,
    pub near: f32,
}

/// The page's matrices are three.js's: column-major, Y up, the model turned -90 deg about X at its root.
/// The model here is as the CAD drew it, so a page matrix M becomes C @ M, C = [[1,0,0],[0,0,-1],[0,1,0]].
/// Returns the 3x4 rows of C @ M.
pub fn page_to_cad(m: &[f32; 16]) -> [f32; 12] {
    let e = |r: usize, c: usize| m[c * 4 + r];
    [e(0, 0), e(0, 1), e(0, 2), e(0, 3), -e(2, 0), -e(2, 1), -e(2, 2), -e(2, 3), e(1, 0), e(1, 1), e(1, 2), e(1, 3)]
}

impl Camera {
    /// From the page camera's matrixWorld (it looks down its own -Z).
    pub fn from_page(m: &[f32; 16], fov_deg: f32, near: f32) -> Camera {
        let a = page_to_cad(m);
        let col = |c: usize| Vec3::new(a[c], a[4 + c], a[8 + c]);
        Camera { eye: col(3), r: col(0).normalize(), u: col(1).normalize(), f: -col(2).normalize(), tan_y: (fov_deg.to_radians() * 0.5).tan(), near }
    }
}

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable, Default)]
struct Globals {
    cam_pos: [f32; 4],
    cam_r: [f32; 4],
    cam_u: [f32; 4],
    cam_f: [f32; 4],
    prev_pos: [f32; 4],
    prev_r: [f32; 4],
    prev_u: [f32; 4],
    prev_f: [f32; 4],
    size: [u32; 2],
    frame: u32,
    n: u32,
    reset: u32,
    mode: u32,
    spf: u32,
    flags: u32,
    denoise: f32,
    hist_w: f32,
    max_hist: f32,
    near: f32,
    surf: [u32; 2],
    vsize: [f32; 2],
    sun: [f32; 4],
    bg: [f32; 4],
    clip: [f32; 4],
    off: [u32; 2],
    white: f32,
    peak: f32,
    jit: [f32; 2],
    out: [u32; 2],
}

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct PassP {
    step: i32,
    sigma_l: f32,
    pad: [f32; 2],
}

#[derive(Clone, Copy)]
pub struct Settings {
    pub denoise: bool,
    pub temporal: bool,
    pub spf_moving: u32,
    pub spf_still: u32,
    /// > 0: while moving, raise samples per frame until a frame costs about this much GPU time
    pub budget_ms: f32,
    pub max_hist: f32,
    /// how many standard deviations of the samples' own noise two pixels may differ by and still be blended
    pub sigma_l: f32,
}

impl Default for Settings {
    fn default() -> Self {
        Settings { denoise: true, temporal: false, spf_moving: 1, spf_still: 1, budget_ms: 0.0, max_hist: 16.0, sigma_l: 4.0 }
    }
}

/// What the page says about the light and the cut. All in the CAD frame.
#[derive(Clone, Copy, PartialEq)]
pub struct Look {
    pub sun: Vec3,
    pub sun_strength: f32,
    /// backdrop, linear
    pub bg: [f32; 3],
    /// section plane [nx, ny, nz, c]: kept where n.p + c >= 0
    pub clip: Option<[f32; 4]>,
    /// the size the page projects onto (device px); None = the picture's own size
    pub vsize: Option<(f32, f32)>,
}

impl Default for Look {
    fn default() -> Self {
        Look { sun: Vec3::new(3.0, -2.0, 4.0).normalize(), sun_strength: 2.4, bg: [0.00802, 0.00913, 0.01161], clip: None, vsize: None }
    }
}

struct Targets {
    w: u32,
    h: u32,
    out_px: wgpu::Buffer,
    staging: wgpu::Buffer,
    guide: [wgpu::Buffer; 2],
    guide_staging: wgpu::Buffer,
    bg_trace: [wgpu::BindGroup; 2],
    bg_pre: [wgpu::BindGroup; 2],
    bg_atrous: [[wgpu::BindGroup; ATROUS_PASSES]; 2],
    bg_resolve: [wgpu::BindGroup; 2],
    bg_blit: wgpu::BindGroup,
}

/// A model on the card that is not the one being drawn: see Renderer::park.
pub struct Parked(SceneGpu);

impl Parked {
    /// what it holds of the card's memory, roughly: its buffers (the BLASes are about as much again)
    pub fn bytes(&self) -> u64 {
        self.0.idx_buf.size() + self.0.vattr_buf.size() + self.0.parts_buf.size() + self.0.motion_buf.size()
    }
}

/// DLSS RAY RECONSTRUCTION (NVIDIA's, through dlss_wgpu; Vulkan only): in place of the tracer's own denoiser
/// while the picture moves, and for the first samples of a picture at rest. It is given the picture as traced
/// and what stands at each pixel (dlss_in.wgsl), and gives back a clean picture (finished by dlss_out.wgsl);
/// it keeps the frames before itself, so each frame's rays leave their pixels at a place it is told (G.jit,
/// flag 32). Ported from the new_codes tracer, where it was first made to work.
#[cfg(feature = "dlss")]
struct Dlss {
    sdk: std::sync::Arc<std::sync::Mutex<dlss_wgpu::DlssSdk>>,
    adapter: wgpu::Adapter,
    l_in: wgpu::BindGroupLayout,
    l_out: wgpu::BindGroupLayout,
    p_in: wgpu::ComputePipeline,
    p_out: wgpu::ComputePipeline,
    per: Option<DlssPer>,
    /// frames it has been given in a row
    run: u32,
    /// frames since its history last started again (`seed`)
    since: u32,
}

/// ... what of it is made for one size of picture
#[cfg(feature = "dlss")]
struct DlssPer {
    /// at the picture's own size (DLAA): at rest, and while moving with `Upscale::Off`
    ctx: dlss_wgpu::ray_reconstruction::DlssRayReconstruction,
    /// enlarging a smaller picture to it while moving, one for each `Upscale` mode, made when first wanted
    up: [Option<dlss_wgpu::ray_reconstruction::DlssRayReconstruction>; 5],
    /// whose the last frame was (None: `ctx`'s): another has no history of it, so it starts afresh
    last: Option<Upscale>,
    /// the picture's size they were made for
    size: (u32, u32),
    /// colour, diffuse, specular, normal + roughness, depth, motion, DLSS's picture
    views: [wgpu::TextureView; 7],
    bg_in: [wgpu::BindGroup; 2],
    bg_out: wgpu::BindGroup,
}

/// The model on the card.
struct SceneGpu {
    parts_buf: wgpu::Buffer,
    idx_buf: wgpu::Buffer,
    vattr_buf: wgpu::Buffer,
    blases: Vec<wgpu::Blas>,
    tlas: wgpu::Tlas,
    parts: Vec<GpuPart>,
    xf: Vec<[f32; 12]>,
    /// where each part stood in the last frame drawn, and whether any has moved since
    xf_prev: Vec<[f32; 12]>,
    xf_moved: bool,
    /// per part, 3x4 rows: takes a point from where the part is to where it was a frame ago
    motion_buf: wgpu::Buffer,
    motion_live: bool,
    hidden: Vec<bool>,
    tlas_dirty: bool,
    parts_dirty: bool,
}

pub struct Renderer {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    globals: wgpu::Buffer,
    pass_bufs: Vec<wgpu::Buffer>,
    scene: Option<SceneGpu>,
    l_trace: wgpu::BindGroupLayout,
    l_pre: wgpu::BindGroupLayout,
    l_atrous: wgpu::BindGroupLayout,
    l_resolve: wgpu::BindGroupLayout,
    l_blit: wgpu::BindGroupLayout,
    p_trace: wgpu::ComputePipeline,
    p_pre: wgpu::ComputePipeline,
    p_atrous: wgpu::ComputePipeline,
    p_resolve: wgpu::ComputePipeline,
    p_blit: wgpu::RenderPipeline,
    targets: Option<Targets>,
    size: (u32, u32),
    pub settings: Settings,
    pub look: Look,
    /// work done, for the proof that a picture at rest costs nothing: frames traced, compute dispatches
    pub n_renders: u64,
    pub n_dispatches: u64,
    /// the surface encodes sRGB itself (an ...Srgb format): hand it linear values
    pub linear_out: bool,
    /// what shows the surface decodes it with a plain 2.4 power (Vulkan on an HDR desktop): encode to suit
    pub power_out: bool,
    /// linear_out to a FLOAT surface (scRGB, 1.0 = 80 nits): the screen's SDR white in those units (hdr.rs)
    pub white: f32,
    /// a float surface on an HDR screen, HDR wanted: the light above the SDR white goes on up to the screen's
    /// `peak` (scRGB units) instead of being clipped (common.wgsl `hdr_out`; `set_hdr`)
    pub hdr: bool,
    pub peak: f32,
    /// rows of the surface ABOVE the picture (the tabbed app's tab strip): the picture is shown below them
    pub top: u32,
    pub n: u32,
    frame: u32,
    parity: usize,
    prev_cam: Option<Camera>,
    last_globals: Globals,
    #[cfg(feature = "dlss")]
    dlss: Option<Dlss>,
    /// DLSS is wanted (made unless DESK_DLSS=0, on a card that has it: see `enable_dlss`)
    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    pub dlss_on: bool,
    /// DLSS enlarges the picture while it moves (see `Upscale`; `set_upscale`): at least this much...
    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    upscale: Upscale,
    /// ...and more if a moving frame would otherwise take longer than floor_ms() (`note_frame`)
    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    auto_up: Upscale,
    /// moving frames in a row over the floor / well under it at the next mode down
    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    slow: u32,
    #[cfg_attr(not(feature = "dlss"), allow(dead_code))]
    fast: u32,
    /// the last frame was traced smaller than the picture: it cannot be added to
    small: bool,
    /// what is on the screen is DLSS's picture of this view (held at rest: see `render`)
    dlss_shown: bool,
}

fn shader(device: &wgpu::Device, name: &str, src: &str) -> wgpu::ShaderModule {
    let src = src.replace("//!include common", include_str!("common.wgsl")).replace("//!include tables", include_str!("tables.wgsl"));
    device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some(name), source: wgpu::ShaderSource::Wgsl(src.into()) })
}

fn e_buf(binding: u32, ty: wgpu::BufferBindingType, vis: wgpu::ShaderStages) -> wgpu::BindGroupLayoutEntry {
    wgpu::BindGroupLayoutEntry { binding, visibility: vis, ty: wgpu::BindingType::Buffer { ty, has_dynamic_offset: false, min_binding_size: None }, count: None }
}
/// with DLSS on, a picture at rest shows DLSS's last moving picture until it has this many samples a pixel;
/// then it is the tracer's own
#[cfg(feature = "dlss")]
const DLSS_UNTIL: u32 = 256;
/// DLSS's frames with less history than this are not shown (see `seed` in render): measured black for the
/// first and still black a frame or two later (2026-10-20)
#[cfg(feature = "dlss")]
const DLSS_WARM: u32 = 4;

const UNI: wgpu::BufferBindingType = wgpu::BufferBindingType::Uniform;
const RO: wgpu::BufferBindingType = wgpu::BufferBindingType::Storage { read_only: true };
const RW: wgpu::BufferBindingType = wgpu::BufferBindingType::Storage { read_only: false };

fn layout(device: &wgpu::Device, label: &str, entries: &[wgpu::BindGroupLayoutEntry]) -> wgpu::BindGroupLayout {
    device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries })
}

fn compute_pipeline(device: &wgpu::Device, label: &str, l: &wgpu::BindGroupLayout, m: &wgpu::ShaderModule) -> wgpu::ComputePipeline {
    let pl = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: Some(label), bind_group_layouts: &[Some(l)], immediate_size: 0 });
    device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: Some(label),
        layout: Some(&pl),
        module: m,
        entry_point: Some("main"),
        compilation_options: Default::default(),
        cache: None,
    })
}

fn bind(device: &wgpu::Device, l: &wgpu::BindGroupLayout, res: &[wgpu::BindingResource]) -> wgpu::BindGroup {
    let entries: Vec<_> = res.iter().enumerate().map(|(i, r)| wgpu::BindGroupEntry { binding: i as u32, resource: r.clone() }).collect();
    device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout: l, entries: &entries })
}

fn basis(c: &Camera, aspect: f32) -> ([f32; 4], [f32; 4], [f32; 4], [f32; 4]) {
    ([c.eye.x, c.eye.y, c.eye.z, c.tan_y], [c.r.x, c.r.y, c.r.z, c.tan_y * aspect], [c.u.x, c.u.y, c.u.z, 0.0], [c.f.x, c.f.y, c.f.z, 0.0])
}

pub fn srgb_to_linear(v: f32) -> f32 {
    if v <= 0.04045 { v / 12.92 } else { ((v + 0.055) / 1.055).powf(2.4) }
}

pub fn linear_to_srgb(v: f32) -> f32 {
    let v = v.clamp(0.0, 1.0);
    if v <= 0.0031308 { v * 12.92 } else { 1.055 * v.powf(1.0 / 2.4) - 0.055 }
}

impl Renderer {
    pub fn new(device: wgpu::Device, queue: wgpu::Queue, surface_format: wgpu::TextureFormat) -> Self {
        let c = wgpu::ShaderStages::COMPUTE;
        let l_trace = layout(
            &device,
            "trace",
            &[
                e_buf(0, UNI, c),
                wgpu::BindGroupLayoutEntry { binding: 1, visibility: c, ty: wgpu::BindingType::AccelerationStructure { vertex_return: false }, count: None },
                e_buf(2, RO, c),
                e_buf(3, RO, c),
                e_buf(4, RO, c),
                e_buf(5, RW, c),
                e_buf(6, RW, c),
                e_buf(7, RW, c),
                e_buf(8, RW, c),
                e_buf(9, RW, c),
            ],
        );
        let l_pre = layout(&device, "pre", &[e_buf(0, UNI, c), e_buf(1, RO, c), e_buf(2, RO, c), e_buf(3, RO, c), e_buf(4, RO, c), e_buf(5, RW, c), e_buf(6, RW, c), e_buf(7, RO, c), e_buf(8, RO, c), e_buf(9, RO, c)]);
        let l_atrous = layout(&device, "atrous", &[e_buf(0, UNI, c), e_buf(1, UNI, c), e_buf(2, RO, c), e_buf(3, RO, c), e_buf(4, RW, c)]);
        let l_resolve = layout(&device, "resolve", &[e_buf(0, UNI, c), e_buf(1, RO, c), e_buf(2, RO, c), e_buf(3, RO, c), e_buf(4, RW, c), e_buf(5, RO, c), e_buf(6, RO, c), e_buf(7, RO, c), e_buf(8, RW, c)]);
        let f = wgpu::ShaderStages::FRAGMENT;
        let l_blit = layout(&device, "blit", &[e_buf(0, UNI, f), e_buf(1, RO, f)]);

        let p_trace = compute_pipeline(&device, "trace", &l_trace, &shader(&device, "trace", include_str!("trace.wgsl")));
        let p_pre = compute_pipeline(&device, "pre", &l_pre, &shader(&device, "pre", include_str!("pre.wgsl")));
        let p_atrous = compute_pipeline(&device, "atrous", &l_atrous, &shader(&device, "atrous", include_str!("atrous.wgsl")));
        let p_resolve = compute_pipeline(&device, "resolve", &l_resolve, &shader(&device, "resolve", include_str!("resolve.wgsl")));
        let m_blit = shader(&device, "blit", include_str!("blit.wgsl"));
        let pl_blit = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&l_blit)], immediate_size: 0 });
        let p_blit = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("blit"),
            layout: Some(&pl_blit),
            vertex: wgpu::VertexState { module: &m_blit, entry_point: Some("vs"), compilation_options: Default::default(), buffers: &[] },
            primitive: Default::default(),
            depth_stencil: None,
            multisample: Default::default(),
            fragment: Some(wgpu::FragmentState { module: &m_blit, entry_point: Some("fs"), compilation_options: Default::default(), targets: &[Some(surface_format.into())] }),
            multiview_mask: None,
            cache: None,
        });

        let globals = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("globals"),
            size: std::mem::size_of::<Globals>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let pass_bufs = (0..ATROUS_PASSES)
            .map(|_| device.create_buffer(&wgpu::BufferDescriptor { label: Some("passp"), size: 16, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false }))
            .collect();

        Renderer {
            device,
            queue,
            globals,
            pass_bufs,
            scene: None,
            l_trace,
            l_pre,
            l_atrous,
            l_resolve,
            l_blit,
            p_trace,
            p_pre,
            p_atrous,
            p_resolve,
            p_blit,
            targets: None,
            size: (1, 1),
            settings: Settings::default(),
            look: Look::default(),
            n_renders: 0,
            n_dispatches: 0,
            linear_out: surface_format.is_srgb(),
            power_out: false,
            white: 1.0,
            hdr: false,
            peak: 1.0,
            top: 0,
            n: 0,
            frame: 0,
            parity: 0,
            prev_cam: None,
            last_globals: Globals::default(),
            #[cfg(feature = "dlss")]
            dlss: None,
            dlss_on: true,
            upscale: Upscale::Off,
            auto_up: Upscale::Off,
            slow: 0,
            fast: 0,
            small: false,
            dlss_shown: false,
        }
    }

    pub fn has_scene(&self) -> bool {
        self.scene.is_some()
    }

    /// Put a model on the card in place of whatever was there. Every part starts shown, where the file has
    /// it, unselected. Returns (upload ms, BLAS build ms).
    pub fn set_scene(&mut self, scene: &Scene) -> (f64, f64) {
        let device = &self.device;
        let t0 = Instant::now();
        let buf = |label: &str, contents: &[u8], usage: wgpu::BufferUsages| device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: Some(label), contents, usage });
        let vb = buf("positions", bytemuck::cast_slice(&scene.positions), wgpu::BufferUsages::BLAS_INPUT);
        let idx_buf = buf("indices", bytemuck::cast_slice(&scene.indices), wgpu::BufferUsages::BLAS_INPUT | wgpu::BufferUsages::STORAGE);
        let vattr_buf = buf("vattr", bytemuck::cast_slice(&scene.vattr), wgpu::BufferUsages::STORAGE);
        let parts_buf = buf("parts", bytemuck::cast_slice(&scene.gpu_parts), wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST);
        self.queue.submit([]);
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        let upload_ms = t0.elapsed().as_secs_f64() * 1e3;

        let t0 = Instant::now();
        let sizes: Vec<wgpu::BlasTriangleGeometrySizeDescriptor> = scene
            .parts
            .iter()
            .map(|p| wgpu::BlasTriangleGeometrySizeDescriptor {
                vertex_format: wgpu::VertexFormat::Float32x3,
                vertex_count: p.vtx_count,
                index_format: Some(wgpu::IndexFormat::Uint32),
                index_count: Some(p.idx_count),
                flags: if p.clear { wgpu::AccelerationStructureGeometryFlags::empty() } else { wgpu::AccelerationStructureGeometryFlags::OPAQUE },
            })
            .collect();
        let blases: Vec<wgpu::Blas> = sizes
            .iter()
            .map(|s| {
                device.create_blas(
                    &wgpu::CreateBlasDescriptor { label: None, flags: wgpu::AccelerationStructureFlags::PREFER_FAST_TRACE, update_mode: wgpu::AccelerationStructureUpdateMode::Build },
                    wgpu::BlasGeometrySizeDescriptors::Triangles { descriptors: vec![s.clone()] },
                )
            })
            .collect();
        let entries: Vec<wgpu::BlasBuildEntry> = scene
            .parts
            .iter()
            .enumerate()
            .map(|(i, p)| wgpu::BlasBuildEntry {
                blas: &blases[i],
                geometry: wgpu::BlasGeometries::TriangleGeometries(vec![wgpu::BlasTriangleGeometry {
                    size: &sizes[i],
                    vertex_buffer: &vb,
                    first_vertex: p.vtx_off,
                    vertex_stride: 12,
                    index_buffer: Some(&idx_buf),
                    first_index: Some(p.idx_off),
                    transform_buffer: None,
                    transform_buffer_offset: None,
                }]),
            })
            .collect();
        let mut enc = device.create_command_encoder(&Default::default());
        enc.build_acceleration_structures(entries.iter(), std::iter::empty());
        self.queue.submit([enc.finish()]);
        device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        let blas_ms = t0.elapsed().as_secs_f64() * 1e3;
        drop(entries);

        let np = scene.parts.len();
        let tlas = device.create_tlas(&wgpu::CreateTlasDescriptor {
            label: Some("tlas"),
            max_instances: np.max(1) as u32,
            flags: wgpu::AccelerationStructureFlags::PREFER_FAST_TRACE,
            update_mode: wgpu::AccelerationStructureUpdateMode::Build,
        });
        let motion_buf = buf("motion", bytemuck::cast_slice(&vec![IDENT; np.max(1)]), wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST);
        self.scene = Some(SceneGpu { parts_buf, idx_buf, vattr_buf, blases, tlas, parts: scene.gpu_parts.clone(), xf: vec![IDENT; np], xf_prev: vec![IDENT; np], xf_moved: false, motion_buf, motion_live: false, hidden: vec![false; np], tlas_dirty: true, parts_dirty: false });
        for i in 0..np {
            self.put_instance(i);
        }
        // the bind groups name the model's buffers
        let (w, h) = self.size;
        self.targets = None;
        self.resize(w, h);
        (upload_ms, blas_ms)
    }

    fn put_instance(&mut self, i: usize) {
        let Some(s) = self.scene.as_mut() else { return };
        s.tlas[i] = if s.hidden[i] { None } else { Some(wgpu::TlasInstance::new(&s.blases[i], s.xf[i], i as u32, 0xff)) };
        s.tlas_dirty = true;
    }

    /// A hidden part is out of the TLAS: no ray of any kind meets it. True if that changed anything.
    pub fn set_hidden(&mut self, i: usize, hidden: bool) -> bool {
        let Some(s) = self.scene.as_mut() else { return false };
        if s.hidden[i] == hidden {
            return false;
        }
        s.hidden[i] = hidden;
        self.put_instance(i);
        true
    }

    /// Where a part stands: 3x4 rows, CAD frame.
    pub fn set_xf(&mut self, i: usize, xf: [f32; 12]) -> bool {
        let Some(s) = self.scene.as_mut() else { return false };
        if s.xf[i] == xf {
            return false;
        }
        s.xf[i] = xf;
        s.xf_moved = true;
        self.put_instance(i);
        true
    }

    pub fn set_selected(&mut self, i: usize, sel: bool) -> bool {
        let Some(s) = self.scene.as_mut() else { return false };
        let f = if sel { s.parts[i].flags | FLAG_SEL } else { s.parts[i].flags & !FLAG_SEL };
        if f == s.parts[i].flags {
            return false;
        }
        s.parts[i].flags = f;
        s.parts_dirty = true;
        true
    }

    /// The model taken OFF THE RENDERER BUT LEFT ON THE CARD (the tabbed app: the tab is no longer the one
    /// shown), with all that was said about its parts. Put back with `unpark`, it is the picture it was
    /// without a file read or a BLAS built.
    pub fn park(&mut self) -> Option<Parked> {
        self.targets = None;
        self.invalidate();
        self.scene.take().map(Parked)
    }

    /// Returns the ms it took (the picture's buffers are made again: they name the model's).
    pub fn unpark(&mut self, p: Parked) -> f64 {
        let t0 = Instant::now();
        self.scene = Some(p.0);
        let (w, h) = self.size;
        self.targets = None;
        self.resize(w, h);
        t0.elapsed().as_secs_f64() * 1e3
    }

    /// (parts hidden, parts not where the file has them, parts selected)
    pub fn counts(&self) -> (usize, usize, usize) {
        match &self.scene {
            Some(s) => (s.hidden.iter().filter(|h| **h).count(), s.xf.iter().filter(|x| **x != IDENT).count(), s.parts.iter().filter(|p| p.flags & FLAG_SEL != 0).count()),
            None => (0, 0, 0),
        }
    }

    /// Forget accumulation and temporal history.
    /// DLSS Ray Reconstruction on this card, if it will. The device must have been made for it
    /// (dlss_wgpu::request_device). -> what to say of it
    #[cfg(feature = "dlss")]
    pub fn enable_dlss(&mut self, adapter: &wgpu::Adapter, project: uuid::Uuid) -> String {
        let sdk = match dlss_wgpu::DlssSdk::new(project, self.device.clone()) {
            Ok(s) => s,
            Err(e) => return format!("DLSS: not used: {e}"),
        };
        let c = wgpu::ShaderStages::COMPUTE;
        let sto = |binding: u32, format: wgpu::TextureFormat| wgpu::BindGroupLayoutEntry {
            binding,
            visibility: c,
            ty: wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format, view_dimension: wgpu::TextureViewDimension::D2 },
            count: None,
        };
        let tex = wgpu::BindGroupLayoutEntry {
            binding: 1,
            visibility: c,
            ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false },
            count: None,
        };
        let f16 = wgpu::TextureFormat::Rgba16Float;
        let l_in = layout(&self.device, "dlss_in", &[e_buf(0, UNI, c), e_buf(1, RO, c), e_buf(2, RO, c), e_buf(3, RO, c), e_buf(4, RO, c), e_buf(5, RO, c), sto(6, f16), sto(7, f16), sto(8, f16), sto(9, f16), sto(10, wgpu::TextureFormat::R32Float), sto(11, f16)]);
        let l_out = layout(&self.device, "dlss_out", &[e_buf(0, UNI, c), tex, e_buf(2, RW, c), e_buf(3, RW, c)]);
        let p_in = compute_pipeline(&self.device, "dlss_in", &l_in, &shader(&self.device, "dlss_in", include_str!("dlss_in.wgsl")));
        let p_out = compute_pipeline(&self.device, "dlss_out", &l_out, &shader(&self.device, "dlss_out", include_str!("dlss_out.wgsl")));
        self.dlss = Some(Dlss { sdk, adapter: adapter.clone(), l_in, l_out, p_in, p_out, per: None, run: 0, since: 0 });
        // (made for the picture's size at the next resize)
        let size = self.size;
        self.size = (0, 0);
        self.resize(size.0, size.1);
        let made = self.dlss.as_ref().is_some_and(|d| d.per.is_some());
        format!("DLSS: Ray Reconstruction {}", if made { "made for this picture" } else { "there (made for each model's picture)" })
    }

    /// DLSS is there on this card (made for each picture's size at its resize; it may still be off: `dlss_on`)
    pub fn dlss_ready(&self) -> bool {
        #[cfg(feature = "dlss")]
        return self.dlss.is_some();
        #[cfg(not(feature = "dlss"))]
        false
    }

    /// The size a moving picture is traced at, if DLSS enlarges it (None: at its own size).
    pub fn moving_size(&self) -> Option<(u32, u32)> {
        #[cfg(feature = "dlss")]
        if let Some(up) = self.dlss.as_ref().and_then(|d| d.per.as_ref()).and_then(|p| p.up[self.moving_upscale() as usize].as_ref()) {
            let r = up.render_resolution();
            return Some((r[0], r[1]));
        }
        None
    }

    /// The enlarging a moving frame gets now: what is set, or more to keep floor_ms().
    pub fn moving_upscale(&self) -> Upscale {
        self.upscale.max(self.auto_up)
    }

    /// DLSS's enlarging to the picture's size in `mode`, made now if it has not been. False: it cannot be.
    #[cfg(feature = "dlss")]
    fn want_up(&mut self, mode: Upscale) -> bool {
        use dlss_wgpu::ray_reconstruction::{DlssRayReconstruction, DlssRayReconstructionDepthMode, DlssRayReconstructionRoughnessMode};
        let (Some(dl), Some(m)) = (self.dlss.as_mut(), mode.mode()) else { return false };
        let Some(per) = dl.per.as_mut() else { return false };
        if per.up[mode as usize].is_none() {
            let (w, h) = self.size;
            let flags = dlss_wgpu::DlssFeatureFlags::HighDynamicRange | dlss_wgpu::DlssFeatureFlags::LowResolutionMotionVectors;
            match DlssRayReconstruction::new([w, h], m, flags, DlssRayReconstructionRoughnessMode::Packed, DlssRayReconstructionDepthMode::Linear, dl.sdk.clone(), &self.device, &self.queue) {
                Ok(c) => per.up[mode as usize] = Some(c),
                Err(e) => {
                    eprintln!("DLSS: no {} enlarging at {w}x{h}: {e}", mode.name());
                    return false;
                }
            }
        }
        true
    }

    pub fn upscale(&self) -> Upscale {
        self.upscale
    }

    /// DLSS's enlarging, made again for the picture's size; the picture starts again.
    /// (each mode's enlarging is made when it is first wanted, and kept: see `want_up`)
    pub fn set_upscale(&mut self, u: Upscale) {
        if self.upscale != u {
            self.upscale = u;
            self.invalidate();
        }
    }

    pub fn set_dlss_on(&mut self, on: bool) {
        if self.dlss_on != on {
            self.dlss_on = on;
            self.invalidate();
        }
    }

    /// Encode for a screen that decodes a plain 2.4 power (see `power_out`); the picture is resolved again.
    pub fn set_power_out(&mut self, on: bool) {
        if self.power_out != on {
            self.power_out = on;
            self.invalidate();
        }
    }

    /// HDR out (see `hdr`), up to `peak` (scRGB units); the picture is resolved again.
    pub fn set_hdr(&mut self, on: bool, peak: f32) {
        if (self.hdr, self.peak) != (on, peak) {
            (self.hdr, self.peak) = (on, peak);
            self.invalidate();
        }
    }

    pub fn set_white(&mut self, w: f32) {
        if self.white != w {
            self.white = w;
            self.invalidate();
        }
    }

    pub fn invalidate(&mut self) {
        self.n = 0;
        self.prev_cam = None;
        self.dlss_shown = false;
    }

    pub fn size(&self) -> (u32, u32) {
        self.size
    }

    pub fn resize(&mut self, w: u32, h: u32) {
        let (w, h) = (w.max(1), h.max(1));
        if self.size == (w, h) && self.targets.is_some() {
            return;
        }
        self.size = (w, h);
        self.invalidate();
        let Some(sc) = self.scene.as_ref() else {
            self.targets = None;
            return;
        };
        let d = &self.device;
        let px = (w * h) as u64;
        let sto = |label: &str, stride: u64, extra: wgpu::BufferUsages| d.create_buffer(&wgpu::BufferDescriptor { label: Some(label), size: px * stride, usage: wgpu::BufferUsages::STORAGE | extra, mapped_at_creation: false });
        let none = wgpu::BufferUsages::empty();
        let (acc_a, acc_b, acc_c) = (sto("acc_a", 16, none), sto("acc_b", 16, none), sto("acc_c", 16, none));
        let other = sto("other", 4, none);
        let guide = [sto("guide0", 16, wgpu::BufferUsages::COPY_SRC), sto("guide1", 16, wgpu::BufferUsages::COPY_SRC)];
        let hist = [sto("hist0", 32, none), sto("hist1", 32, none)];
        let fa = sto("fa", 16, none);
        let fb = sto("fb", 16, none);
        let out_px = sto("out", 4, wgpu::BufferUsages::COPY_SRC);
        // what the window is handed (resolve.wgsl): out_px, or out_px encoded for a plain-2.4 screen (.x of 8
        // bytes), or HDR halves (all 8)
        let shown_px = sto("shown", 8, none);
        let stg = |size: u64| d.create_buffer(&wgpu::BufferDescriptor { label: Some("staging"), size, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let (staging, guide_staging) = (stg(px * 4), stg(px * 16));
        let g = self.globals.as_entire_binding();
        let mk_trace = |p: usize| bind(d, &self.l_trace, &[g.clone(), sc.tlas.as_binding(), sc.parts_buf.as_entire_binding(), sc.idx_buf.as_entire_binding(), sc.vattr_buf.as_entire_binding(), acc_a.as_entire_binding(), guide[p].as_entire_binding(), acc_b.as_entire_binding(), acc_c.as_entire_binding(), other.as_entire_binding()]);
        let mk_pre = |p: usize| bind(d, &self.l_pre, &[g.clone(), acc_a.as_entire_binding(), guide[p].as_entire_binding(), guide[1 - p].as_entire_binding(), hist[1 - p].as_entire_binding(), hist[p].as_entire_binding(), fa.as_entire_binding(), acc_b.as_entire_binding(), acc_c.as_entire_binding(), sc.motion_buf.as_entire_binding()]);
        let mk_atrous = |p: usize| -> [wgpu::BindGroup; ATROUS_PASSES] {
            std::array::from_fn(|i| {
                let (src, dst) = if i % 2 == 0 { (&fa, &fb) } else { (&fb, &fa) };
                bind(d, &self.l_atrous, &[g.clone(), self.pass_bufs[i].as_entire_binding(), guide[p].as_entire_binding(), src.as_entire_binding(), dst.as_entire_binding()])
            })
        };
        // odd pass count: the final result lands in fb
        let mk_resolve = |p: usize| bind(d, &self.l_resolve, &[g.clone(), guide[p].as_entire_binding(), acc_a.as_entire_binding(), fb.as_entire_binding(), out_px.as_entire_binding(), acc_b.as_entire_binding(), acc_c.as_entire_binding(), other.as_entire_binding(), shown_px.as_entire_binding()]);
        #[cfg(feature = "dlss")]
        if let Some(dl) = self.dlss.as_mut() {
            use dlss_wgpu::ray_reconstruction::{DlssRayReconstruction, DlssRayReconstructionDepthMode, DlssRayReconstructionRoughnessMode};
            dl.run = 0;
            let flags = dlss_wgpu::DlssFeatureFlags::HighDynamicRange | dlss_wgpu::DlssFeatureFlags::LowResolutionMotionVectors;
            // (the textures are the picture's size; a smaller picture uses their top left: partial_texture_size)
            // (the ones that enlarge a smaller picture to this size while it moves are made when first wanted)
            // THE CONTEXTS ARE KEPT WHEN THE SIZE IS: a tab shown again (unpark) remakes the buffers, which name
            // its model, but DLSS's contexts belong to the size alone. Made afresh on every change of tab, a new
            // context's first pictures were black, and that black was then HELD on screen (see `hold`) until
            // the still picture reached DLSS_UNTIL samples: seconds of black on a large window (user, 2026-10-20).
            let kept = dl.per.take().filter(|o| o.size == (w, h)).map(|o| (o.ctx, o.up));
            let made = match kept {
                Some(k) => Ok(k),
                None => DlssRayReconstruction::new([w, h], dlss_wgpu::DlssPerfQualityMode::Dlaa, flags, DlssRayReconstructionRoughnessMode::Packed, DlssRayReconstructionDepthMode::Linear, dl.sdk.clone(), d, &self.queue).map(|c| (c, Default::default())),
            };
            match made {
                Ok((ctx, up)) => {
                    let tex = |label: &str, format: wgpu::TextureFormat| {
                        d.create_texture(&wgpu::TextureDescriptor {
                            label: Some(label),
                            size: wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 },
                            mip_level_count: 1,
                            sample_count: 1,
                            dimension: wgpu::TextureDimension::D2,
                            format,
                            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::STORAGE_BINDING,
                            view_formats: &[],
                        })
                        .create_view(&Default::default())
                    };
                    let f16 = wgpu::TextureFormat::Rgba16Float;
                    let views = [tex("dlss colour", f16), tex("dlss diffuse", f16), tex("dlss specular", f16), tex("dlss normal", f16), tex("dlss depth", wgpu::TextureFormat::R32Float), tex("dlss motion", f16), tex("dlss out", f16)];
                    let mk_in = |p: usize| {
                        let mut res = vec![g.clone(), acc_a.as_entire_binding(), acc_c.as_entire_binding(), guide[p].as_entire_binding(), sc.parts_buf.as_entire_binding(), sc.motion_buf.as_entire_binding()];
                        res.extend(views[..6].iter().map(wgpu::BindingResource::TextureView));
                        bind(d, &dl.l_in, &res)
                    };
                    let bg_in = [mk_in(0), mk_in(1)];
                    let bg_out = bind(d, &dl.l_out, &[g.clone(), wgpu::BindingResource::TextureView(&views[6]), out_px.as_entire_binding(), shown_px.as_entire_binding()]);
                    dl.per = Some(DlssPer { ctx, up, last: None, size: (w, h), views, bg_in, bg_out });
                }
                Err(e) => eprintln!("DLSS: not used at {w}x{h}: {e}"),
            }
        }
        let t = Targets {
            w,
            h,
            bg_trace: [mk_trace(0), mk_trace(1)],
            bg_pre: [mk_pre(0), mk_pre(1)],
            bg_atrous: [mk_atrous(0), mk_atrous(1)],
            bg_resolve: [mk_resolve(0), mk_resolve(1)],
            bg_blit: bind(d, &self.l_blit, &[g.clone(), shown_px.as_entire_binding()]),
            out_px,
            staging,
            guide,
            guide_staging,
        };
        self.targets = Some(t);
    }

    /// Render one frame. `changed`: the camera or anything in the picture changed since the last frame, so
    /// accumulation restarts. `keep`: the last frame is still a picture of this scene from nearby (the camera
    /// moved, parts moved, were hidden or picked), so its light is carried over, each surface point looked up
    /// where it was; not after a resize, a new model, a new cut or new light.
    /// Returns None (and submits nothing) when there is no model or the image is already converged.
    pub fn render(&mut self, cam: &Camera, changed: bool, keep: bool, surface: Option<(&wgpu::TextureView, u32, u32)>) -> Option<wgpu::SubmissionIndex> {
        self.scene.as_ref()?;
        // TRACED SMALLER WHILE IT MOVES, DLSS making it the window's size (`Upscale`). At rest it is traced at
        // its own size; samples of a smaller picture cannot be added to, so rest starts again from nothing.
        #[cfg(feature = "dlss")]
        let up_mode = self.moving_upscale();
        #[cfg(feature = "dlss")]
        let small = changed && self.dlss_on && up_mode != Upscale::Off && self.want_up(up_mode);
        #[cfg(not(feature = "dlss"))]
        let small = false;
        let reset = changed || self.n == 0 || self.small;
        self.small = small;
        if !reset && self.n >= MAX_SPP {
            return None;
        }
        if changed && !keep {
            self.prev_cam = None;
        }
        let t = self.targets.as_ref().expect("resize first");
        let s = self.settings;
        let spf = if reset { s.spf_moving.clamp(1, MAX_SPF) } else { s.spf_still.clamp(1, MAX_SPP - self.n) };
        self.n = if reset { spf } else { self.n + spf };
        self.frame = self.frame.wrapping_add(1);
        let temporal = s.temporal && s.denoise;
        // DLSS, if it is there and wanted: while the picture moves, and for a picture's first samples at rest
        #[cfg(feature = "dlss")]
        let dlss_can = self.dlss_on && self.dlss.as_ref().is_some_and(|d| d.per.is_some());
        // DLSS CLEANS THE MOVING PICTURE ONLY. At rest its last picture stays on the screen while the tracer
        // gathers samples under it at full speed (`hold`: nothing is resolved or shown anew) until there are
        // DLSS_UNTIL a pixel, and then the tracer's own picture is shown. (Run on every frame at rest it cost a
        // 1907x2041 window 25-70 ms a frame, a sample a frame at 12 fps: the picture took 20-70 s to settle and
        // the window waited on every frame. 2026-10-16.)
        #[cfg(feature = "dlss")]
        let use_dlss = dlss_can && changed;
        #[cfg(feature = "dlss")]
        let hold = dlss_can && !changed && self.dlss_shown && self.n <= DLSS_UNTIL;
        // A DLSS FRAME WITH (ALMOST) NO HISTORY IS NOT SHOWN. Its picture came out black (the first frames
        // after a change of tab, a new model, a resize), and `hold` then kept that black on screen until the
        // still picture reached DLSS_UNTIL samples -- seconds on a large window, gone at the first touch, which
        // gave DLSS a history (user, 2026-10-20). Such a frame still goes to DLSS, which builds its history from
        // it, but what is shown is the tracer's own picture; and it is never the one held. DLSS_WARM frames on,
        // DLSS's picture is shown as before.
        // (traced smaller, the tracer's picture is not the window's: then it is only not held)
        #[cfg(feature = "dlss")]
        let seed = use_dlss && {
            let dl = self.dlss.as_ref().unwrap();
            let restart = dl.run == 0 || self.prev_cam.is_none() || dl.per.as_ref().unwrap().last != small.then_some(up_mode);
            restart || dl.since + 1 < DLSS_WARM
        };
        #[cfg(feature = "dlss")]
        let own = !use_dlss || (seed && !small);
        #[cfg(not(feature = "dlss"))]
        let (use_dlss, hold, own) = (false, false, true);
        // the size traced: the picture's own, or DLSS's smaller one for it
        #[allow(unused_mut)]
        let mut rs = (t.w, t.h);
        #[allow(unused_mut)]
        let mut jitter = [0.0f32; 2];
        #[cfg(feature = "dlss")]
        if let Some(per) = self.dlss.as_ref().and_then(|d| d.per.as_ref()) {
            let ctx = if small { per.up[up_mode as usize].as_ref().unwrap() } else { &per.ctx };
            if small {
                let r = ctx.render_resolution();
                rs = (r[0].clamp(1, t.w), r[1].clamp(1, t.h));
            }
            if use_dlss && reset {
                jitter = ctx.suggested_jitter(self.frame, [rs.0, rs.1]);
            }
        }
        let mut mode = 0;
        let mut hist_w = 0.0;
        if temporal {
            if reset {
                mode = 1;
                self.parity ^= 1;
            } else {
                mode = 2;
                hist_w = 12.0 * (1.0 - (self.n as f32 / 48.0)).clamp(0.0, 1.0);
            }
        }
        let vsize = self.look.vsize.unwrap_or((t.w as f32, t.h as f32));
        let aspect = vsize.0 / vsize.1;
        let (cp, cr, cu, cf) = basis(cam, aspect);
        // no previous camera: point the reprojection somewhere that can never validate
        let (pp, pr, pu, pf) = match self.prev_cam {
            Some(pc) => basis(&pc, aspect),
            None => ([1e9, 1e9, 1e9, cp[3]], cr, cu, cf),
        };
        let (sw, sh) = surface.map(|x| (x.1, x.2)).unwrap_or((t.w, t.h));
        let l = self.look;
        let g = Globals {
            cam_pos: cp,
            cam_r: cr,
            cam_u: cu,
            cam_f: cf,
            prev_pos: pp,
            prev_r: pr,
            prev_u: pu,
            prev_f: pf,
            size: [rs.0, rs.1],
            frame: self.frame,
            n: self.n,
            reset: reset as u32,
            mode,
            spf,
            flags: if l.clip.is_some() { 2 } else { 0 } | if s.denoise { 0 } else { 1 } | if self.linear_out { 8 } else { 0 } | if self.power_out { 16 } else { 0 } | if use_dlss { 32 } else { 0 } | if self.hdr { 64 } else { 0 },
            denoise: if s.denoise { 1.0 } else { 0.0 },
            hist_w,
            max_hist: s.max_hist,
            near: cam.near,
            surf: [sw, sh.saturating_sub(self.top).max(1)],
            // (the same view over fewer pixels)
            vsize: [vsize.0 * rs.0 as f32 / t.w as f32, vsize.1 * rs.1 as f32 / t.h as f32],
            sun: [l.sun.x, l.sun.y, l.sun.z, l.sun_strength],
            bg: [l.bg[0], l.bg[1], l.bg[2], 1.0],
            clip: l.clip.unwrap_or([0.0; 4]),
            off: [0, self.top.min(sh.saturating_sub(1))],
            white: self.white,
            peak: self.peak,
            jit: jitter,
            out: [t.w, t.h],
        };
        self.last_globals = g;
        self.queue.write_buffer(&self.globals, 0, bytemuck::bytes_of(&g));
        if s.denoise {
            for i in 0..ATROUS_PASSES {
                self.queue.write_buffer(&self.pass_bufs[i], 0, bytemuck::bytes_of(&PassP { step: 1 << i, sigma_l: s.sigma_l, pad: [0.0; 2] }));
            }
        }
        let p = self.parity;
        let (gx, gy) = (rs.0.div_ceil(8), rs.1.div_ceil(8));
        let mut enc = self.device.create_command_encoder(&Default::default());
        // parts shown, hidden or moved since the last frame: the TLAS is built again (the BLASes never are)
        let sc = self.scene.as_mut().unwrap();
        if sc.parts_dirty {
            self.queue.write_buffer(&sc.parts_buf, 0, bytemuck::cast_slice(&sc.parts));
            sc.parts_dirty = false;
        }
        if reset && (sc.xf_moved || sc.motion_live) {
            // each moved part's step back to where the last frame had it: was * now^-1
            let m4 = |r: &[f32; 12]| glam::Mat4::from_cols_array(&[r[0], r[4], r[8], 0.0, r[1], r[5], r[9], 0.0, r[2], r[6], r[10], 0.0, r[3], r[7], r[11], 1.0]);
            let mot: Vec<[f32; 12]> = sc
                .xf
                .iter()
                .zip(&sc.xf_prev)
                .map(|(now, was)| {
                    if now == was {
                        return IDENT;
                    }
                    let m = (m4(was) * m4(now).inverse()).to_cols_array();
                    [m[0], m[4], m[8], m[12], m[1], m[5], m[9], m[13], m[2], m[6], m[10], m[14]]
                })
                .collect();
            self.queue.write_buffer(&sc.motion_buf, 0, bytemuck::cast_slice(&mot));
            sc.motion_live = sc.xf_moved;
            sc.xf_moved = false;
            sc.xf_prev.clone_from(&sc.xf);
        }
        if sc.tlas_dirty {
            enc.build_acceleration_structures(std::iter::empty(), std::iter::once(&sc.tlas));
            sc.tlas_dirty = false;
        }
        {
            let mut cp = enc.begin_compute_pass(&Default::default());
            cp.set_pipeline(&self.p_trace);
            cp.set_bind_group(0, &t.bg_trace[p], &[]);
            cp.dispatch_workgroups(gx, gy, 1);
            self.n_dispatches += 2;
            #[cfg(feature = "dlss")]
            if use_dlss {
                let dl = self.dlss.as_ref().unwrap();
                cp.set_pipeline(&dl.p_in);
                cp.set_bind_group(0, &dl.per.as_ref().unwrap().bg_in[p], &[]);
                cp.dispatch_workgroups(gx, gy, 1);
            }
            if !own || hold {
                // (its own denoise and its own finishing are DLSS's this frame; held: no picture is made)
            } else if s.denoise {
                cp.set_pipeline(&self.p_pre);
                cp.set_bind_group(0, &t.bg_pre[p], &[]);
                cp.dispatch_workgroups(gx, gy, 1);
                cp.set_pipeline(&self.p_atrous);
                for i in 0..ATROUS_PASSES {
                    cp.set_bind_group(0, &t.bg_atrous[p][i], &[]);
                    cp.dispatch_workgroups(gx, gy, 1);
                }
                self.n_dispatches += 1 + ATROUS_PASSES as u64;
            }
            if own && !hold {
                cp.set_pipeline(&self.p_resolve);
                cp.set_bind_group(0, &t.bg_resolve[p], &[]);
                cp.dispatch_workgroups(gx, gy, 1);
            }
        }
        self.n_renders += 1;
        #[cfg(feature = "dlss")]
        if use_dlss {
            use dlss_wgpu::ray_reconstruction::{DlssRayReconstructionRenderParameters, DlssRayReconstructionSpecularGuide};
            let fresh = self.prev_cam.is_none();
            let dl = self.dlss.as_mut().unwrap();
            let adapter = dl.adapter.clone();
            let mut first = dl.run == 0 || fresh;
            dl.run += 1;
            let per = dl.per.as_mut().unwrap();
            // (the other one has seen none of the frames before this: it starts afresh)
            let now = small.then_some(up_mode);
            first |= per.last != now;
            per.last = now;
            dl.since = if first { 0 } else { dl.since + 1 };
            let v = &per.views;
            let params = DlssRayReconstructionRenderParameters {
                diffuse_albedo: &v[1],
                specular_albedo: &v[2],
                normals: &v[3],
                roughness: None,
                color: &v[0],
                depth: &v[4],
                motion_vectors: &v[5],
                // (what a glossy surface mirrors is taken to move as the surface does)
                specular_guide: DlssRayReconstructionSpecularGuide::SpecularMotionVectors(&v[5]),
                transparency_overlay: None,
                color_before_transparency: None,
                screen_space_subsurface_scattering_guide: None,
                depth_of_field_guide: None,
                responsivity_mask: None,
                alpha: None,
                dlss_output_alpha: None,
                dlss_output: &v[6],
                reset: first,
                // (the rays left each pixel at its centre + jitter: the picture is shifted the other way)
                jitter_offset: [-jitter[0], -jitter[1]],
                partial_texture_size: small.then_some([rs.0, rs.1]),
                motion_vector_scale: None,
            };
            let ctx = if small { per.up[up_mode as usize].as_mut().unwrap() } else { &mut per.ctx };
            match ctx.render(params, &mut enc, &adapter) {
                Ok(cmd) => {
                    let dl = self.dlss.as_ref().unwrap();
                    let mut after = self.device.create_command_encoder(&Default::default());
                    if !own {
                        let mut cp = after.begin_compute_pass(&Default::default());
                        cp.set_pipeline(&dl.p_out);
                        cp.set_bind_group(0, &dl.per.as_ref().unwrap().bg_out, &[]);
                        cp.dispatch_workgroups(t.w.div_ceil(8), t.h.div_ceil(8), 1);
                    }
                    self.n_dispatches += 2;
                    if let Some((view, _, _)) = surface {
                        self.blit(&mut after, view, true);
                    }
                    self.prev_cam = Some(*cam);
                    self.dlss_shown = !seed;
                    return Some(self.queue.submit([enc.finish(), cmd, after.finish()]));
                }
                Err(e) => {
                    // (it has failed: this frame goes without a picture of its own, the next is the tracer's)
                    eprintln!("DLSS: turned off: {e}");
                    self.dlss_on = false;
                }
            }
        }
        // (held, DLSS's history is still of this view: the next movement goes on from it)
        #[cfg(feature = "dlss")]
        if !use_dlss && !hold {
            if let Some(dl) = self.dlss.as_mut() {
                dl.run = 0;
            }
        }
        self.dlss_shown &= hold;
        if let Some((view, _, _)) = surface {
            self.blit(&mut enc, view, true);
        }
        self.prev_cam = Some(*cam);
        Some(self.queue.submit([enc.finish()]))
    }

    fn blit(&self, enc: &mut wgpu::CommandEncoder, view: &wgpu::TextureView, draw: bool) {
        let bg = self.look.bg.map(|v| if self.linear_out { (v * self.white) as f64 } else if self.power_out { v.powf(1.0 / 2.4) as f64 } else { linear_to_srgb(v) as f64 });
        let mut rp = enc.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: None,
            color_attachments: &[Some(wgpu::RenderPassColorAttachment { view, depth_slice: None, resolve_target: None, ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color { r: bg[0], g: bg[1], b: bg[2], a: 1.0 }), store: wgpu::StoreOp::Store } })],
            depth_stencil_attachment: None,
            timestamp_writes: None,
            occlusion_query_set: None,
            multiview_mask: None,
        });
        if let (true, Some(t)) = (draw, self.targets.as_ref()) {
            rp.set_pipeline(&self.p_blit);
            rp.set_bind_group(0, &t.bg_blit, &[]);
            rp.draw(0..3, 0..1);
        }
    }

    /// No model yet: the backdrop alone.
    pub fn clear(&mut self, view: &wgpu::TextureView) {
        let mut enc = self.device.create_command_encoder(&Default::default());
        self.blit(&mut enc, view, false);
        self.queue.submit([enc.finish()]);
    }

    fn read(&self, src: &wgpu::Buffer, staging: &wgpu::Buffer) -> Vec<u8> {
        let mut enc = self.device.create_command_encoder(&Default::default());
        enc.copy_buffer_to_buffer(src, 0, staging, 0, src.size());
        self.queue.submit([enc.finish()]);
        let slice = staging.slice(..);
        slice.map_async(wgpu::MapMode::Read, |r| r.unwrap());
        self.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        let v = slice.get_mapped_range().unwrap().to_vec();
        staging.unmap();
        v
    }

    /// Read back the image as presented (RGBA8, sRGB). Empty without a model.
    pub fn read_pixels(&mut self) -> Vec<u8> {
        match self.targets.as_ref() {
            Some(t) => self.read(&t.out_px, &t.staging),
            None => vec![],
        }
    }

    /// The first-hit distance along each pixel's centre ray (< 0: backdrop) and the part met there, as of
    /// the last restart of the picture.
    pub fn read_guide(&mut self) -> Vec<(f32, u32)> {
        let Some(t) = self.targets.as_ref() else { return vec![] };
        if self.small {
            return vec![]; // (traced smaller: not a pixel each)
        }
        let raw = self.read(&t.guide[self.parity], &t.guide_staging);
        raw.chunks_exact(16).map(|c| (f32::from_le_bytes([c[4], c[5], c[6], c[7]]), u32::from_le_bytes([c[12], c[13], c[14], c[15]]))).collect()
    }

    /// Samples a frame follow the card: as many as fit the time a frame may take (`budget_ms`, which the
    /// shell sets from the display's refresh), found from the time the last frame DID take, so a slower
    /// card gives fewer samples at the same frame rate instead of fewer frames.
    pub fn note_frame(&mut self, changed: bool, gpu_ms: f64) {
        let b = self.settings.budget_ms as f64;
        let step = |n: u32, ms: f64, b: f64, up: f64| -> u32 {
            // towards the count that would just fill the budget, a part of the way each frame (one slow
            // frame is not a slow card), at once when over it
            let want = (n as f64 * (0.9 * b / ms.max(0.05))).clamp(1.0, MAX_SPF as f64);
            let next = if ms > b { want.floor() } else { n as f64 + ((want - n as f64) * 0.25).clamp(-4.0, up) };
            (next.round() as u32).clamp(1, MAX_SPF)
        };
        if changed && b > 0.0 {
            self.settings.spf_moving = step(self.settings.spf_moving, gpu_ms, b, 4.0);
        }
        // NEVER UNDER 24 FPS WHILE MOVING (user, 2026-10-17): a moving frame that takes longer than floor_ms() at
        // one sample a pixel is traced smaller, DLSS enlarging it a mode more; back down a mode once the frame
        // would be well inside it there. A few frames in a row each way: one slow frame is not a slow card.
        #[cfg(feature = "dlss")]
        if changed && self.dlss_on && self.dlss_ready() {
            let now = self.moving_upscale();
            let lower = self.upscale.max(self.auto_up.down());
            if gpu_ms > 0.9 * floor_ms() && self.settings.spf_moving <= 1 && now != Upscale::Ultra {
                self.fast = 0;
                self.slow += 1;
                if self.slow >= 3 {
                    self.auto_up = now.up();
                    self.slow = 0;
                }
            } else if lower < now && gpu_ms * lower.frac() / now.frac() < 0.6 * floor_ms() {
                self.slow = 0;
                self.fast += 1;
                if self.fast >= 30 {
                    self.auto_up = self.auto_up.down();
                    self.fast = 0;
                }
            } else {
                (self.slow, self.fast) = (0, 0);
            }
        }
        // AT REST THE PICTURE IS GATHERED IN LONG FRAMES, whatever the display's rate: nothing is moving,
        // so nobody needs 240 of them a second, and every frame shown costs its denoise and its present.
        // STILL_MS of the card a frame gets the picture to its cap in the fewest frames, and so in the
        // least time at full power -- which is what a pedal press costs.
        let s = &mut self.settings.spf_still;
        if changed {
            *s = self.settings.spf_moving.max(1);
        } else {
            *s = step(*s, gpu_ms, STILL_MS, MAX_SPF as f64);
        }
    }

    pub fn wait(&self, idx: wgpu::SubmissionIndex) {
        self.device.poll(wgpu::PollType::Wait { submission_index: Some(idx), timeout: None }).unwrap();
    }
}
