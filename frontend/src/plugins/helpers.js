export function toRgb(color, fade = 0) {
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

  r = Math.round(r + (255 - r) * fade);
  g = Math.round(g + (255 - g) * fade);
  b = Math.round(b + (255 - b) * fade);

  return `rgb(${r}, ${g}, ${b})`;
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
