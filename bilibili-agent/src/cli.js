import { searchBilibili } from "./search.js";

async function main() {
  const keyword = process.argv[2];
  const maxResults = Number(process.argv[3] || 10);

  if (!keyword) {
    console.error(JSON.stringify({ error: "keyword required" }));
    process.exit(1);
  }

  try {
    const results = await searchBilibili(keyword, { headless: true, maxResults });
    process.stdout.write(
      JSON.stringify(
        {
          keyword,
          count: results.length,
          results,
        },
        null,
        2
      )
    );
  } catch (error) {
    console.error(JSON.stringify({ error: error.message || String(error) }));
    process.exit(1);
  }
}

main();
