//!include common
// The picture DLSS Ray Reconstruction gives back (linear light, at the picture's own size G.out), finished as resolve.wgsl finishes the
// tracer's own: linear -> sRGB, no tone curve; packed rgba8, the picture (outp) and what the window is handed
// (shown: encoded for a plain-2.4 screen when flags bit 4 says so; HDR, bit 6: unclipped scRGB halves).

@group(0) @binding(0) var<uniform> G: Globals;
@group(0) @binding(1) var t_in: texture_2d<f32>;
@group(0) @binding(2) var<storage, read_write> outp: array<u32>;
@group(0) @binding(3) var<storage, read_write> shown: array<vec2u>;

fn srgb(c: vec3f) -> vec3f {
  let x = clamp(c, vec3f(0.0), vec3f(1.0));
  return select(1.055 * pow(x, vec3f(1.0 / 2.4)) - 0.055, x * 12.92, x <= vec3f(0.0031308));
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= G.out.x || gid.y >= G.out.y) { return; }
  let raw = textureLoad(t_in, vec2i(gid.xy), 0).rgb;
  let lin = clamp(raw, vec3f(0.0), vec3f(1.0));
  let idx = gid.y * G.out.x + gid.x;
  let pic = pack4x8unorm(vec4f(srgb(lin), 1.0));
  outp[idx] = pic;
  if ((G.flags & 64u) != 0u) { shown[idx] = pack_hdr(hdr_out(raw, G.white, G.peak)); return; }
  shown[idx] = vec2u(select(pic, pack4x8unorm(vec4f(pow(lin, vec3f(1.0 / 2.4)), 1.0)), (G.flags & 16u) != 0u), 0u);
}
