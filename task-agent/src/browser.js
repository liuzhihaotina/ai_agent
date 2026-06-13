import path from "path";
import { chromium } from "playwright";

const DEFAULT_USER_DATA_DIR = path.join(
  process.env.LOCALAPPDATA || "C:/Users/liuzh/AppData/Local",
  "Google",
  "Chrome",
  "User Data"
);
const USER_DATA_DIR = process.env.TASK_AGENT_USER_DATA_DIR || DEFAULT_USER_DATA_DIR;
const PROFILE_DIR = process.env.TASK_AGENT_PROFILE_DIR || "Default";

export async function launchBrowser({ headless = true } = {}) {
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless,
    args: [`--profile-directory=${PROFILE_DIR}`],
  });

  const page = await context.newPage();

  return { context, page };
}
