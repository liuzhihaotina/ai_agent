import express from "express";
import { searchBilibili } from "./search.js";

const app = express();
app.use(express.json());

app.post("/search", async (req, res) => {
  const { keyword } = req.body;

  if (!keyword) {
    return res.status(400).json({ error: "keyword required" });
  }

  try {
    const results = await searchBilibili(keyword);

    res.json({
      keyword,
      count: results.length,
      results
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(3000, () => {
  console.log("🚀 Bilibili Agent running on http://localhost:3000");
});