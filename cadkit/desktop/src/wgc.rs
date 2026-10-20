//! Windows Graphics Capture (the selftest's capture; DESK_CAPTURE=dda for desktop duplication): the window's own frames as DWM composes them for the
//! screen, in scRGB float on an HDR desktop -- the same colour handling as desktop duplication (dda.rs), but
//! of this window alone, so other windows may cover it (it must not be minimised). Cropped to the client area
//! and turned into sRGB bytes exactly as dda.rs does. Each capture waits (up to 0.4 s) for a frame composed
//! after it was asked for: frames come only when the window changes, and a stale one once read the white level
//! off a frame from before the green calibration square was drawn (3x too bright), the SDR white level calibrated on the same green element.
use crate::cap::{client_size, client_to_screen};
use crate::dda::{half, srgb};
use std::cell::RefCell;
use std::time::{Duration, Instant};
use windows::Graphics::Capture::{Direct3D11CaptureFrame, Direct3D11CaptureFramePool, GraphicsCaptureItem, GraphicsCaptureSession};
use windows::Graphics::DirectX::Direct3D11::IDirect3DDevice;
use windows::Graphics::DirectX::DirectXPixelFormat;
use windows::Win32::Foundation::{HMODULE, HWND, RECT};
use windows::Win32::Graphics::Direct3D::D3D_DRIVER_TYPE_HARDWARE;
use windows::Win32::Graphics::Direct3D11::*;
use windows::Win32::Graphics::Dwm::{DWMWA_EXTENDED_FRAME_BOUNDS, DwmGetWindowAttribute};
use windows::Win32::Graphics::Dxgi::IDXGIDevice;
use windows::Win32::System::Performance::{QueryPerformanceCounter, QueryPerformanceFrequency};
use windows::Win32::System::WinRT::Direct3D11::{CreateDirect3D11DeviceFromDXGIDevice, IDirect3DDxgiInterfaceAccess};
use windows::Win32::System::WinRT::Graphics::Capture::IGraphicsCaptureItemInterop;
use windows::core::Interface;

struct Wgc {
    device: ID3D11Device,
    ctx: ID3D11DeviceContext,
    d3d: IDirect3DDevice,
    pool: Direct3D11CaptureFramePool,
    _session: GraphicsCaptureSession,
    size: windows::Graphics::SizeInt32,
    staging: Option<(ID3D11Texture2D, u32, u32)>,
    scale: f32,
}

thread_local! { static WGC: RefCell<Option<Wgc>> = const { RefCell::new(None) }; }

/// The selftest captures with this, not desktop duplication (validated 2026-10-16: the same levels as desktop
/// duplication on an HDR desktop, DX12 and Vulkan alike), so its window need not be on top.
pub fn wanted() -> bool {
    std::env::var("DESK_CAPTURE").map_or(true, |v| v != "dda")
}

pub fn init(h: isize) -> Result<String, String> {
    let e = |s: &str, e: windows::core::Error| format!("window capture unavailable: {s}: {e}");
    unsafe {
        let (mut device, mut ctx) = (None, None);
        D3D11CreateDevice(None, D3D_DRIVER_TYPE_HARDWARE, HMODULE::default(), D3D11_CREATE_DEVICE_BGRA_SUPPORT, None, D3D11_SDK_VERSION, Some(&mut device), None, Some(&mut ctx)).map_err(|x| e("D3D11CreateDevice", x))?;
        let (device, ctx) = (device.unwrap(), ctx.unwrap());
        let dxgi = device.cast::<IDXGIDevice>().map_err(|x| e("IDXGIDevice", x))?;
        let d3d = CreateDirect3D11DeviceFromDXGIDevice(&dxgi).map_err(|x| e("CreateDirect3D11DeviceFromDXGIDevice", x))?.cast::<IDirect3DDevice>().map_err(|x| e("IDirect3DDevice", x))?;
        let interop = windows::core::factory::<GraphicsCaptureItem, IGraphicsCaptureItemInterop>().map_err(|x| e("IGraphicsCaptureItemInterop", x))?;
        let item: GraphicsCaptureItem = interop.CreateForWindow(HWND(h as _)).map_err(|x| e("CreateForWindow", x))?;
        let size = item.Size().map_err(|x| e("Size", x))?;
        let pool = Direct3D11CaptureFramePool::CreateFreeThreaded(&d3d, DirectXPixelFormat::R16G16B16A16Float, 2, size).map_err(|x| e("CreateFreeThreaded", x))?;
        let session = pool.CreateCaptureSession(&item).map_err(|x| e("CreateCaptureSession", x))?;
        let _ = session.SetIsBorderRequired(false);
        let _ = session.SetIsCursorCaptureEnabled(false);
        session.StartCapture().map_err(|x| e("StartCapture", x))?;
        let scale = std::env::var("APP_SDR_SCALE").ok().and_then(|v| v.parse().ok()).unwrap_or(1.0);
        WGC.with(|c| *c.borrow_mut() = Some(Wgc { device, ctx, d3d, pool, _session: session, size, staging: None, scale }));
        Ok(format!("window capture (Windows Graphics Capture, scRGB float frames): window {}x{}", size.Width, size.Height))
    }
}

/// Now, on the clock frames are stamped with (SystemRelativeTime: QueryPerformanceCounter in 100 ns).
fn now_100ns() -> i64 {
    let (mut c, mut f) = (0i64, 1i64);
    unsafe {
        let _ = QueryPerformanceCounter(&mut c);
        let _ = QueryPerformanceFrequency(&mut f);
    }
    (c as i128 * 10_000_000 / f.max(1) as i128) as i64
}

/// The newest frame, preferring one composed after `since`: frames come only when the window changes, so a
/// window that has not changed gives none and the newest older one (or the last kept) stands.
fn newest(w: &mut Wgc, since: i64, wait: Duration) -> Option<Direct3D11CaptureFrame> {
    let t0 = Instant::now();
    let mut got: Option<Direct3D11CaptureFrame> = None;
    loop {
        match w.pool.TryGetNextFrame() {
            Ok(f) => got = Some(f),
            Err(_) => {
                let fresh = got.as_ref().and_then(|f| f.SystemRelativeTime().ok()).is_some_and(|t| t.Duration >= since);
                if fresh || t0.elapsed() > wait {
                    return got;
                }
                std::thread::sleep(Duration::from_millis(5));
            }
        }
    }
}

/// What the last capture held brighter than the SDR white (an HDR picture's highlights, which the 8-bit
/// capture clips): pixels whose brightest channel is over 1.02x it, and the brightest, in nits.
pub static OVER_WHITE: std::sync::Mutex<(u64, f32)> = std::sync::Mutex::new((0, 0.0));

/// `green`: client rect of an opaque rgb(0,255,0) element, used to calibrate the SDR white level (as dda.rs).
pub fn capture(h: isize, green: Option<[f64; 4]>) -> Result<(u32, u32, Vec<u8>), String> {
    let (cw, ch) = client_size(h);
    let (sx, sy) = client_to_screen(h, 0, 0);
    // what the capture holds is the window's extended frame: find the client area inside it
    let mut fr = RECT::default();
    unsafe { DwmGetWindowAttribute(HWND(h as _), DWMWA_EXTENDED_FRAME_BOUNDS, &mut fr as *mut RECT as *mut _, std::mem::size_of::<RECT>() as u32) }.map_err(|x| format!("DwmGetWindowAttribute: {x}"))?;
    let (ox, oy) = (sx - fr.left, sy - fr.top);
    let since = now_100ns();
    WGC.with(|c| unsafe {
        let mut c = c.borrow_mut();
        let Some(w) = c.as_mut() else { return Err("not initialised".to_string()) };
        // a frame arrives when the window's content changes: take the newest, or keep the last one
        if let Some(f) = newest(w, since, Duration::from_millis(400)) {
            let cs = f.ContentSize().map_err(|x| format!("ContentSize: {x}"))?;
            if cs.Width != w.size.Width || cs.Height != w.size.Height {
                // the window changed size: the pool follows, and the next frame is of the new size
                w.size = cs;
                w.pool.Recreate(&w.d3d, DirectXPixelFormat::R16G16B16A16Float, 2, cs).map_err(|x| format!("Recreate: {x}"))?;
                drop(f);
                let Some(f2) = newest(w, since, Duration::from_millis(800)) else { return Err("no frame after the window's resize".to_string()) };
                copy(w, &f2)?;
            } else {
                copy(w, &f)?;
            }
        }
        let Some((st, tw, th)) = w.staging.clone() else { return Err("no window frame arrived".to_string()) };
        let mut m = D3D11_MAPPED_SUBRESOURCE::default();
        w.ctx.Map(&st, 0, D3D11_MAP_READ, 0, Some(&mut m)).map_err(|x| format!("Map: {x}"))?;
        let px = |x: i32, y: i32| -> Option<&[u8]> {
            let (xx, yy) = (x + ox, y + oy);
            if xx < 0 || yy < 0 || xx >= tw as i32 || yy >= th as i32 {
                return None;
            }
            Some(std::slice::from_raw_parts((m.pData as *const u8).add(yy as usize * m.RowPitch as usize + xx as usize * 8), 8))
        };
        let h16 = |p: &[u8], i: usize| half(u16::from_le_bytes([p[i * 2], p[i * 2 + 1]]));
        if let Some(r) = green {
            let (mut s, mut n) = (0.0f32, 0.0f32);
            for y in (r[1] + 6.0) as i32..(r[1] + r[3] - 6.0) as i32 {
                for x in (r[0] + 6.0) as i32..(r[0] + r[2] - 6.0) as i32 {
                    if let Some(p) = px(x, y) {
                        s += h16(p, 1);
                        n += 1.0;
                    }
                }
            }
            if n > 0.0 && s / n > 0.05 {
                w.scale = s / n;
            }
        }
        let mut buf = vec![0u8; (cw * ch * 4) as usize];
        let (mut over, mut top) = (0u64, 0.0f32);
        for y in 0..ch as i32 {
            for x in 0..cw as i32 {
                let Some(p) = px(x, y) else { continue };
                let t = ((y as u32 * cw + x as u32) * 4) as usize;
                let m = h16(p, 0).max(h16(p, 1)).max(h16(p, 2));
                top = top.max(m);
                over += (m > 1.02 * w.scale) as u64;
                for k in 0..3 {
                    buf[t + k] = srgb(h16(p, k) / w.scale);
                }
                buf[t + 3] = 255;
            }
        }
        w.ctx.Unmap(&st, 0);
        *OVER_WHITE.lock().unwrap() = (over, top * 80.0);
        Ok((cw, ch, buf))
    })
}

unsafe fn copy(w: &mut Wgc, f: &Direct3D11CaptureFrame) -> Result<(), String> {
    unsafe {
        let tex: ID3D11Texture2D = f.Surface().map_err(|x| format!("Surface: {x}"))?.cast::<IDirect3DDxgiInterfaceAccess>().map_err(|x| format!("IDirect3DDxgiInterfaceAccess: {x}"))?.GetInterface().map_err(|x| format!("GetInterface: {x}"))?;
        let mut d = D3D11_TEXTURE2D_DESC::default();
        tex.GetDesc(&mut d);
        if w.staging.as_ref().is_none_or(|s| (s.1, s.2) != (d.Width, d.Height)) {
            d.Usage = D3D11_USAGE_STAGING;
            d.BindFlags = 0;
            d.CPUAccessFlags = D3D11_CPU_ACCESS_READ.0 as u32;
            d.MiscFlags = 0;
            let mut st = None;
            w.device.CreateTexture2D(&d, None, Some(&mut st)).map_err(|x| format!("CreateTexture2D: {x}"))?;
            w.staging = Some((st.unwrap(), d.Width, d.Height));
        }
        w.ctx.CopyResource(&w.staging.as_ref().unwrap().0, &tex);
        Ok(())
    }
}

/// (SDR white level in scRGB units, frames are float)
pub fn scale() -> (f32, bool) {
    WGC.with(|c| c.borrow().as_ref().map(|w| (w.scale, true)).unwrap_or((1.0, true)))
}
