//!include common
// What DLSS Ray Reconstruction is given (dlss feature, gpu.rs `Dlss`), written out of the tracer's own buffers
// as the textures it wants: the picture as traced (linear light, noisy), what the surface at each pixel is (its
// diffuse and specular colour, its normal and roughness, how far it is), and where it was a frame ago.
// (Ported from the new_codes tracer's, where it was first proved; the parts here are rigid, so where a point
// was is its part's motion alone.)

struct Part { idx_off: u32, vtx_off: u32, flags: u32, pad: u32, color: vec4f, mr: vec4f }
struct Mot { r0: vec4f, r1: vec4f, r2: vec4f }

@group(0) @binding(0) var<uniform> G: Globals;
@group(0) @binding(1) var<storage, read> acc_a: array<vec4f>;
@group(0) @binding(2) var<storage, read> acc_c: array<vec4f>;
@group(0) @binding(3) var<storage, read> guide: array<Guide>;
@group(0) @binding(4) var<storage, read> parts: array<Part>;
@group(0) @binding(5) var<storage, read> motion: array<Mot>;
@group(0) @binding(6) var o_color: texture_storage_2d<rgba16float, write>;
@group(0) @binding(7) var o_diff: texture_storage_2d<rgba16float, write>;
@group(0) @binding(8) var o_spec: texture_storage_2d<rgba16float, write>;
@group(0) @binding(9) var o_nrm: texture_storage_2d<rgba16float, write>;     // a: roughness
@group(0) @binding(10) var o_depth: texture_storage_2d<r32float, write>;     // along the camera's forward, mm
@group(0) @binding(11) var o_motion: texture_storage_2d<rgba16float, write>; // xy: to where it was, px

const FAR = 200000.0;

// how much of the light a glossy surface of base reflectance f0 gives back in all, seen at cosine nv
fn gloss_albedo(f0: vec3f, rough: f32, nv: f32) -> vec3f {
  let c0 = vec4f(-1.0, -0.0275, -0.572, 0.022);
  let c1 = vec4f(1.0, 0.0425, 1.04, -0.04);
  let r = rough * c0 + c1;
  let a004 = min(r.x * r.x, exp2(-9.28 * nv)) * r.x + r.y;
  let ab = vec2f(-1.04, 1.04) * a004 + r.zw;
  return f0 * ab.x + ab.y;
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= G.size.x || gid.y >= G.size.y) { return; }
  let idx = gid.y * G.size.x + gid.x;
  let px = vec2i(gid.xy);
  let g = guide[idx];
  let col = (acc_a[idx].rgb + acc_c[idx].rgb) / max(f32(G.n), 1.0);
  // (while the picture moves every ray of a frame leaves the pixel at the same place: see trace.wgsl)
  var jit = vec2f(0.0);
  if (G.reset != 0u) { jit = G.jit; }
  let at = vec2f(gid.xy) + 0.5 + jit;
  let d = ray_dir(at, G.vsize, G.cam_r, G.cam_u, G.cam_f, G.cam_pos.w);
  var p = G.cam_pos.xyz + d * FAR;
  var depth = FAR;
  var diff = vec3f(0.0);
  var spec = vec3f(0.0);
  var n = -d;
  var rough = 1.0;
  var pw = p;
  if (g.depth >= 0.0) {
    let part = parts[g.id];
    let base = unpack4x8unorm(g.albedo).rgb;
    n = oct_dec(g.n);
    rough = part.mr.y;
    diff = base * (1.0 - part.mr.x);
    spec = gloss_albedo(mix(vec3f(0.04), base, part.mr.x), rough, max(dot(n, -d), 1e-3));
    p = G.cam_pos.xyz + d * g.depth;
    depth = g.depth * dot(d, G.cam_f.xyz);
    let m = motion[g.id];
    pw = vec3f(dot(m.r0.xyz, p) + m.r0.w, dot(m.r1.xyz, p) + m.r1.w, dot(m.r2.xyz, p) + m.r2.w);
  }
  var mv = vec2f(0.0);
  let e = pw - G.prev_pos.xyz;
  let z = dot(e, G.prev_f.xyz);
  if (z > 0.0) {
    let ndc = vec2f(dot(e, G.prev_r.xyz) / (z * G.prev_r.w), dot(e, G.prev_u.xyz) / (z * G.prev_pos.w));
    mv = vec2f((ndc.x * 0.5 + 0.5) * G.vsize.x, (0.5 - ndc.y * 0.5) * G.vsize.y) - at;
  }
  textureStore(o_color, px, vec4f(col, 1.0));
  textureStore(o_diff, px, vec4f(diff, 1.0));
  textureStore(o_spec, px, vec4f(spec, 1.0));
  textureStore(o_nrm, px, vec4f(n, rough));
  textureStore(o_depth, px, vec4f(depth, 0.0, 0.0, 0.0));
  textureStore(o_motion, px, vec4f(mv, 0.0, 0.0));
}
