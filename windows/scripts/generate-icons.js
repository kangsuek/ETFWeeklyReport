#!/usr/bin/env node
/**
 * favicon.svg → Windows .ico 아이콘 생성 스크립트
 *
 * 사용법: node scripts/generate-icons.js
 * 필요: sharp, png-to-ico (devDependency)
 */
const sharp = require('sharp');
const pngToIco = require('png-to-ico');
const path = require('path');
const fs = require('fs');

const SVG_SOURCE = path.join(__dirname, '..', '..', 'frontend', 'public', 'favicon.svg');
const ICONS_DIR = path.join(__dirname, '..', 'icons');

// ICO에 포함할 크기들
const ICO_SIZES = [16, 24, 32, 48, 64, 128, 256];

async function main() {
  console.log('=== Windows 아이콘 생성 ===');
  console.log(`SVG 소스: ${SVG_SOURCE}`);

  if (!fs.existsSync(SVG_SOURCE)) {
    console.error(`ERROR: SVG 파일을 찾을 수 없습니다: ${SVG_SOURCE}`);
    process.exit(1);
  }

  fs.mkdirSync(ICONS_DIR, { recursive: true });

  const svgBuffer = fs.readFileSync(SVG_SOURCE);

  // 각 크기의 PNG 생성 (임시)
  const pngBuffers = [];
  for (const size of ICO_SIZES) {
    const pngBuffer = await sharp(svgBuffer)
      .resize(size, size)
      .png()
      .toBuffer();
    pngBuffers.push(pngBuffer);
    console.log(`  생성: ${size}x${size} PNG`);
  }

  // ICO 파일 생성
  const icoPath = path.join(ICONS_DIR, 'icon.ico');
  const icoBuffer = await pngToIco(pngBuffers);
  fs.writeFileSync(icoPath, icoBuffer);
  console.log(`  생성: icon.ico`);

  // electron-builder용 256x256 PNG도 생성 (fallback)
  const pngPath = path.join(ICONS_DIR, 'icon.png');
  await sharp(svgBuffer)
    .resize(256, 256)
    .png()
    .toFile(pngPath);
  console.log(`  생성: icon.png (256x256)`);

  console.log('\n아이콘 생성 완료!');
}

main().catch((err) => {
  console.error('아이콘 생성 실패:', err);
  process.exit(1);
});
