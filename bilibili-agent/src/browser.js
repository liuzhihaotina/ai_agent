import { chromium } from "playwright";
import fs from "fs";

const AUTH_PATH = "./storage/auth.json";

export async function launchBrowser({ headless = false } = {}) {
  const browser = await chromium.launch({
    headless
  });

  const context = fs.existsSync(AUTH_PATH)
    ? await browser.newContext({ storageState: AUTH_PATH })
    : await browser.newContext();

  const page = await context.newPage();

  return { browser, context, page };
}

export async function saveAuth(context) {
  await context.storageState({ path: AUTH_PATH });
}
