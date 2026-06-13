import * as cheerio from "cheerio";

export function parseResults(html) {
  const $ = cheerio.load(html);

  const items = [];

  $(".video-item").each((_, el) => {
    const title = $(el).find(".bili-video-card__info--tit").text().trim();
    const url = "https:" + $(el).find("a").attr("href");
    const up = $(el).find(".bili-video-card__info--author").text().trim();

    items.push({
      title,
      url,
      up
    });
  });

  return items;
}