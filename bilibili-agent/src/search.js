import { launchBrowser, saveAuth } from "./browser.js";

export async function searchBilibili(keyword, options = {}) {
  const { headless = true, maxResults = 10 } = options;
  const { browser, context, page } = await launchBrowser({ headless });

  try {
    await page.goto(
      `https://search.bilibili.com/all?keyword=${encodeURIComponent(keyword)}`,
      { waitUntil: "domcontentloaded" }
    );

    await page.waitForSelector(".bili-video-card, .video-list, .search-page");

    const results = await page.evaluate((limit) => {
      const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();
      const cards = Array.from(
        document.querySelectorAll(".bili-video-card, .video-list-item, .video-item")
      );

      return cards.slice(0, limit).map((card) => {
        const titleEl =
          card.querySelector(".bili-video-card__info--tit") ||
          card.querySelector(".title") ||
          card.querySelector("a[href]");
        const linkEl = card.querySelector("a[href]");
        const authorEl =
          card.querySelector(".bili-video-card__info--author") ||
          card.querySelector(".up-name") ||
          card.querySelector(".author");

        const href = linkEl?.getAttribute("href") || "";
        const url = href
          ? href.startsWith("http")
            ? href
            : `https:${href}`
          : "";

        return {
          title: normalize(titleEl?.textContent),
          url,
          up: normalize(authorEl?.textContent),
        };
      }).filter((item) => item.title || item.url || item.up);
    }, maxResults);

    await saveAuth(context);
    return results;
  } finally {
    await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

export default searchBilibili;

