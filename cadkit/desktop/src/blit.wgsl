//!include common
@group(0) @binding(0) var<uniform> G: Globals;
@group(0) @binding(1) var<storage, read> outp: array<vec2u>;

@vertex
fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
  let p = vec2f(f32((i << 1u) & 2u), f32(i & 2u));
  return vec4f(p * 2.0 - 1.0, 0.0, 1.0);
}

@fragment
fn fs(@builtin(position) pos: vec4f) -> @location(0) vec4f {
  let uv = (pos.xy - vec2f(G.off)) / vec2f(G.surf);
  let q = min(vec2u(uv * vec2f(G.out)), G.out - 1u);
  let s = outp[q.y * G.out.x + q.x];
  // (flags bit 6, HDR: scRGB as it is, finished by resolve.wgsl)
  if ((G.flags & 64u) != 0u) { return vec4f(unpack2x16float(s.x), unpack2x16float(s.y).x, 1.0); }
  let c = unpack4x8unorm(s.x).rgb;
  // (flags bit 3: the surface encodes sRGB itself, so it is handed the linear value)
  if ((G.flags & 8u) != 0u) { return vec4f(select(pow((c + 0.055) / 1.055, vec3f(2.4)), c / 12.92, c <= vec3f(0.04045)) * G.white, 1.0); }
  // (flags bit 4, a screen that decodes a plain 2.4 power: resolve.wgsl has already encoded for it)
  return vec4f(c, 1.0);
}
