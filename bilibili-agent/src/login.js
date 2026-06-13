import { launchBrowser, saveAuth } from "./browser.js";

async function login() {
  const { context, page } = await launchBrowser();

  await page.goto("https://www.bilibili.com");

  console.log("👉 请在浏览器中扫码登录B站...");

  // 等待用户登录成功（检测头像出现）
  await page.waitForSelector(".header-avatar-wrap, .bili-avatar", {
    timeout: 0
  });

  console.log("✅ 登录成功");

  await saveAuth(context);

  console.log("💾 登录状态已保存");
  process.exit(0);
}

login();