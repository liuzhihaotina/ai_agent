运行步骤
1️⃣ 安装依赖
npm install
npx playwright install
2️⃣ 登录一次（扫码）
npm run login
3️⃣ 启动 Agent
npm start
4️⃣ 调用搜索
curl -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{"keyword":"人工智能"}'