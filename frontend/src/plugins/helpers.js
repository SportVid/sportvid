// Shared by toRgb/getContrastColor: parses "#rgb"/"#rrggbb" and applies the
// same white-blend `fade` (0 = color unchanged, 1 = white) both use, so the
// two stay in sync -- getContrastColor needs the *displayed* (post-fade)
// pixel, not the raw swatch color, to judge readability correctly.
function fadedRgb(color, fade = 0) {
  let c = color.startsWith("#") ? color.slice(1) : color;

  if (c.length === 3) {
    c = c
      .split("")
      .map((ch) => ch + ch)
      .join("");
  }

  const num = parseInt(c, 16);

  let r = (num >> 16) & 0xff;
  let g = (num >> 8) & 0xff;
  let b = num & 0xff;

  r = r + (255 - r) * fade;
  g = g + (255 - g) * fade;
  b = b + (255 - b) * fade;

  return [r, g, b];
}

export function toRgb(color, fade = 0) {
  const [r, g, b] = fadedRgb(color, fade);
  return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
}

// Picks whichever of black/white reads better on top of `color` (after the
// same white-blend `fade` toRgb(color, fade) would paint as the background),
// using WCAG relative luminance instead of a fixed "light vs. dark hex"
// threshold. Needed because team colors come from a user-editable mapping
// (visualization store's teamColorMapping) -- any hardcoded '#fff' becomes
// unreadable the moment someone picks a light team color (white, yellow,
// pink, cyan, ...).
export function getContrastColor(color, fade = 0) {
  const [r, g, b] = fadedRgb(color, fade);

  // sRGB -> linear, per WCAG.
  const lin = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  const luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);

  // Contrast ratio formula is (L1 + 0.05) / (L2 + 0.05) with L1 the lighter
  // of the two. White has L=1, black has L=0, so this compares both without
  // needing an extra branch per color.
  const contrastWithWhite = 1.05 / (luminance + 0.05);
  const contrastWithBlack = (luminance + 0.05) / 0.05;
  return contrastWithBlack >= contrastWithWhite ? "#000000" : "#FFFFFF";
}
// export function keyInObj(key, obj) {
//   if (typeof obj !== 'object') return false;
//   return Object.prototype.hasOwnProperty.call(obj, key);
// }
// export function isEqual(x, y) {
//   return JSON.stringify(x) === JSON.stringify(y);
// }
// export function lsplit(x, sep, maxsplit) {
//   x = x.split(sep);
//   const result = x.splice(0, maxsplit);
//   if (x.length) result.push(x.join(sep));
//   return result;
// }
// export function getHash(x) {
//   const md5 = require('crypto').createHash('md5');
//   return md5.update(JSON.stringify(x)).digest('hex');
// }
// export function repPlace(x, y) {
//   const string = y.replace(
//     /{(\w+)}/g,
//     (withDelimiters, withoutDelimiters) =>
//     keyInObj(withoutDelimiters, x) ?
//       x[withoutDelimiters] : withDelimiters
//   );
//   return string;
// }
// export function isMobile() {
//   const devices = [
//     'Android', 'webOS', 'iPhone', 'iPod',
//     'BlackBerry', 'IEMobile', 'Opera Mini',
//   ];
//   const filter = new RegExp(devices.join('|'), 'i');
//   if (filter.test(navigator.userAgent)) {
//     return true;
//   }
//   return false;
// }
