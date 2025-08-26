export function toRgba(color, alpha = 1) {
  let c = color.startsWith("#") ? color.slice(1) : color;

  if (c.length === 3 || c.length === 4) {
    c = c
      .split("")
      .map((ch) => ch + ch)
      .join("");
  }

  const hasAlpha = c.length === 8;

  const r = parseInt(c.substring(0, 2), 16);
  const g = parseInt(c.substring(2, 4), 16);
  const b = parseInt(c.substring(4, 6), 16);
  let a = alpha;

  if (hasAlpha) {
    const aHex = parseInt(c.substring(6, 8), 16);
    a = (aHex / 255) * alpha;
  }

  return `rgba(${r},${g},${b},${a})`;
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
