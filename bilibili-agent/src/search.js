import { launchBrowser, saveAuth } from "./browser.js";
import { parseResults } from "./parser.js";

export async function searchBilibili(keyword) {
  const { context, page } = await launchBrowser();

  await page.goto(`https://search.bilibili.com/all?keyword=${encodeURIComponent(keyword)}`);

  await page.waitForSelector(".video-list");

  const html = await page.content();

  const results = parseResults(html);

  await saveAuth(context);

  return results;
}