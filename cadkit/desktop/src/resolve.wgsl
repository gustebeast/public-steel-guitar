//!include common
// The picture: the guide's samples (smoothed, their colour put back) and the others (as they came), each
// by its share of the pixel; linear -> sRGB, no tone curve (as the reference: Standard view); packed rgba8.
// Twice: `outp` is the picture (captures, the page's comparisons), `shown` is what the window is handed:
// the same 8 bits in .x, or (HDR, flags bit 6) the light unclipped, as scRGB halves (common.wgsl `hdr_out`).

@group(0) @binding(0) var<uniform> G: Globals;
@group(0) @binding(1) var<storage, read> guide: array<Guide>;
@group(0) @binding(2) var<storage, read> acc_a: array<vec4f>;
@group(0) @binding(3) var<storage, read> filt: array<vec4f>;
@group(0) @binding(4) var<storage, read_write> outp: array<u32>;
@group(0) @binding(5) var<storage, read> acc_b: array<vec4f>;
@group(0) @binding(6) var<storage, read> acc_c: array<vec4f>;
@group(0) @binding(7) var<storage, read> other_id: array<u32>;
@group(0) @binding(8) var<storage, read_write> shown: array<vec2u>;

// THE EDGE OF A MOVING PICTURE. A pixel on an edge has a few samples of the thing next door (the "other"
// heap): the right share of the pixel, but few and so grainy while the picture moves. What they met is
// known (other_id), and the pixels next door that show that very thing have its light already smoothed:
// their colour stands in as a prior worth PRIOR samples, which the pixel's own samples outweigh as they
// come in. So an edge is smooth while moving, and at rest it is the samples' own.
const PRIOR = 8.0;
fn smoothed(qi: u32) -> vec3f {
  let a = acc_a[qi];
  return filt[qi].rgb * acc_b[qi].rgb / a.w;
}

fn srgb(c: vec3f) -> vec3f {
  let x = clamp(c, vec3f(0.0), vec3f(1.0));
  return select(1.055 * pow(x, vec3f(1.0 / 2.4)) - 0.055, x * 12.92, x <= vec3f(0.0031308));
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= G.size.x || gid.y >= G.size.y) { return; }
  let idx = gid.y * G.size.x + gid.x;
  let a = acc_a[idx];
  var c = acc_c[idx].rgb;
  let n_other = f32(G.n) - a.w;
  let oid = other_id[idx];
  let den = (G.flags & 1u) == 0u && G.denoise > 0.0;
  if (den && n_other > 0.5 && n_other < PRIOR * 8.0 && oid != OTHER_MIXED && oid != OTHER_NONE) {
    var found = vec4f(0.0);
    if (oid == OTHER_BACKDROP) {
      found = vec4f(G.bg.rgb, 1.0);
    } else {
      let g = guide[idx];
      let own = g.depth >= 0.0 && g.id == oid;      // another face of the same part
      let n = oct_dec(g.n);
      for (var dy = -2; dy <= 2; dy++) {
        for (var dx = -2; dx <= 2; dx++) {
          if (dx == 0 && dy == 0) { continue; }
          let q = vec2i(gid.xy) + vec2i(dx, dy);
          if (q.x < 0 || q.y < 0 || q.x >= i32(G.size.x) || q.y >= i32(G.size.y)) { continue; }
          let qi = u32(q.y) * G.size.x + u32(q.x);
          let gq = guide[qi];
          if (gq.depth < 0.0 || gq.id != oid || acc_a[qi].w < 0.5) { continue; }
          if (own && dot(oct_dec(gq.n), n) > 0.9) { continue; }
          let w = 1.0 / f32(dx * dx + dy * dy);
          found += vec4f(smoothed(qi), 1.0) * w;
        }
      }
    }
    if (found.w > 0.0) { c = (c + found.rgb / found.w * PRIOR) * (n_other / (n_other + PRIOR)); }
  }
  if (a.w > 0.5) {
    if (den && guide[idx].depth >= 0.0) {
      c += filt[idx].rgb * acc_b[idx].rgb;      // the light, smoothed, x the colours it fell on
    } else {
      c += a.rgb;
    }
  }
  let raw = c / f32(G.n);
  let lin = clamp(raw, vec3f(0.0), vec3f(1.0));
  let pic = pack4x8unorm(vec4f(srgb(lin), 1.0));
  outp[idx] = pic;
  if ((G.flags & 64u) != 0u) { shown[idx] = pack_hdr(hdr_out(raw, G.white, G.peak)); return; }
  // A screen that decodes with a plain 2.4 power (flags bit 4: Vulkan on an HDR Windows desktop) is handed
  // the picture encoded for THAT, here, before the 8 bits: re-encoding the 8-bit sRGB in the blit merged 13
  // of the 256 levels and skipped steps in the shadows.
  shown[idx] = vec2u(select(pic, pack4x8unorm(vec4f(pow(lin, vec3f(1.0 / 2.4)), 1.0)), (G.flags & 16u) != 0u), 0u);
}
