// Figma SVG 아이콘을 expo-image로 그대로 쓰기 위해 svg를 에셋으로 등록
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
config.resolver.assetExts.push("svg");

module.exports = config;
