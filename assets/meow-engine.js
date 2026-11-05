/*
 * Local browser port of the app's Meowizer.swift conversion rules.
 * Source: MeowKeyboard 2.6.1 (61), checked 2026-11-04.
 * SHA256: 954b260fdf1b1c3c9bcf67bf7215b62f85ad5e3290e7fb9fac60d9f6ae48ba1b
 * No requests, persistence, telemetry, or random output.
 */
(function (root, factory) {
  'use strict';
  const engine = factory();
  if (typeof module === 'object' && module.exports) module.exports = engine;
  else root.EpiyaMeow = engine;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const segmenter = typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function'
    ? new Intl.Segmenter('zh', { granularity: 'grapheme' }) : null;
  const rules = [
    ['你们', '主人们'], ['我们', '喵们'], ['洗手', '舔爪爪'], ['吃饭', '用餐'],
    ['舒服', '苏服'], ['生气', '炸毛'], ['开心', '翘尾巴'], ['难过', '耷耳朵'],
    ['傻子', '臭杂鱼~'], ['我', '本喵'], ['你', '主人'], ['了', '惹'],
    ['操', '喵了个咪'], ['吃', '享用'], ['喝', '吸溜'], ['拿', '叼走'],
    ['走', '溜达'], ['睡', '打盹'], ['床', '窝'], ['啊', '啊鸣~'],
    ['吧', '叭'], ['呀', '呀咪']
  ];
  const safeFaces = [
    '(=^.^=)', '(^._.^)', '(=^x^=)', '(=^-ω-^=)', 'ฅ(>ω<*ฅ)',
    'ฅ(=´▽`=)ฅ', '(=ↀωↀ=)', '/ᐠ > ˕ <マ', '₍^ >ヮ<^₎',
    '(ฅ´ω`ฅ)', '(=^･ω･^=)', 'ฅ^._.^ฅ', '(ΦωΦ)', '^ ̳ᴗ ̫ ᴗ ̳^'
  ];
  const calmTails = ['喵', '喵~', '呀', '叭'];
  const sassyTails = ['~', '喵~', '呀咪~', '叭~', '喵呜~', '哼哼喵~'];
  const punctuation = new Set(['。', '！', '？', '!', '?']);
  const emotional = ['翘尾巴', '炸毛', '耷耳朵', '打盹', '喜欢', '讨厌', '困', '嘛', '喵呜'];
  // Foundation CharacterSet.whitespacesAndNewlines, not JavaScript trim().
  const whitespace = /^[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200b\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200b\u2028\u2029\u202f\u205f\u3000]+$/gu;

  function characters(text) {
    if (!segmenter) throw new Error('当前浏览器不支持准确的 Unicode 字符分段，请使用更新的浏览器体验喵化。');
    return Array.from(segmenter.segment(text), entry => entry.segment);
  }
  function stableScore(text) {
    let hash = 5381n;
    for (const scalar of text) hash = BigInt.asIntN(64, hash * 33n + BigInt(scalar.codePointAt(0)));
    return Number((hash < 0n ? -hash : hash) % 100n);
  }
  function containsAny(text, words) {
    // Swift's String matching respects complete, canonically equivalent Characters.
    const chars = characters(text).map(char => char.normalize('NFC'));
    return words.some(word => {
      const target = Array.from(word);
      return chars.some((_, i) => target.every((char, j) => chars[i + j] === char));
    });
  }
  function replacePhrases(text) {
    // Foundation replacement searches can end before ZWJ, unlike String.contains.
    // Preserve the joiner and everything following it verbatim during replacement.
    let chars = text.split('\u200d').flatMap((part, index) =>
      index ? ['\u200d', ...characters(part)] : characters(part));
    for (const [from, to] of rules) {
      const target = Array.from(from), next = [];
      for (let i = 0; i < chars.length;) {
        if (target.every((char, j) => chars[i + j]?.normalize('NFC') === char)) {
          next.push(...Array.from(to)); i += target.length;
        } else { next.push(chars[i]); i += 1; }
      }
      chars = next;
    }
    return chars.join('');
  }
  function isEmotional(text) { return containsAny(text, emotional); }
  function tail(text) {
    const score = stableScore(text), choices = isEmotional(text) || score >= 72 ? sassyTails : calmTails;
    return choices[score % choices.length];
  }
  function softenEnding(text) {
    const chars = characters(text), ending = [];
    while (chars.length && punctuation.has(chars[chars.length - 1])) ending.unshift(chars.pop());
    let output = chars.join('');
    if (output.endsWith('吗')) output = output.slice(0, -1) + '嘛~';
    else if (output.endsWith('呢')) output = output.slice(0, -1) + '呐~';
    else if (output.endsWith('啦') || output.endsWith('呀咪')) output += '~';
    return output.endsWith('~') ? output : output + ending.join('');
  }
  function addMeowAfterPunctuation(text) {
    let output = '';
    for (const char of characters(text)) {
      output += char;
      if (punctuation.has(char) && !output.endsWith('喵')) output += '喵';
    }
    return output;
  }
  function face(text) {
    if (containsAny(text, ['翘尾巴', '喜欢'])) return '₍^ >ヮ<^₎';
    if (containsAny(text, ['炸毛', '讨厌', '不'])) return '(=｀ω´=)';
    if (containsAny(text, ['困', '打盹'])) return '^ ̳ᴗ ̫ ᴗ ̳^';
    if (characters(text).length <= 5) return ['(=^.^=)', '(^._.^)', '(=^x^=)'][stableScore(text) % 3];
    return safeFaces[stableScore(text) % safeFaces.length];
  }
  function attachFace(text, mode) {
    if (mode === 'off') return false;
    if (mode === 'always' || mode === 'everySentence') return true;
    if (mode === 'emotion') return isEmotional(text);
    const score = stableScore(text);
    return score < (isEmotional(text) ? 82 : characters(text).length <= 6 ? 24 : 42);
  }
  function transform(input, frequency = 'natural') {
    if (typeof input !== 'string') throw new TypeError('喵化输入必须是文字。');
    let output = input.replace(whitespace, '');
    if (!output) return input;
    output = replacePhrases(output);
    output = addMeowAfterPunctuation(softenEnding(output));
    if (!output.endsWith('喵') && !output.endsWith('喵~') && !output.endsWith('~')) output += tail(output);
    return attachFace(output, frequency) ? output + ' ' + face(output) : output;
  }
  return Object.freeze({
    transform,
    available: Boolean(segmenter),
    modes: Object.freeze(['natural', 'everySentence', 'emotion', 'off']),
    sourceVersion: '2.6.1 (61)',
    sourceSha256: '954b260fdf1b1c3c9bcf67bf7215b62f85ad5e3290e7fb9fac60d9f6ae48ba1b'
  });
});
