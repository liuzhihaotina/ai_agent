import { launchBrowser } from "./browser.js";

const TASK_PAGE_URL = "http://localhost:3000";
const STORAGE_KEY = "task-dashboard-data";
const STATUS_OPTIONS = ["待处理", "进行中", "已完成", "已关闭"];

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function getSearchFields(field) {
  return field === "creator"
    ? ["creator"]
    : field === "name"
      ? ["name"]
      : field === "status"
        ? ["status"]
        : ["name", "creator", "status"];
}

async function waitForTaskTable(page) {
  await page.waitForFunction(
    () => {
      const rows = document.querySelectorAll("#taskTableBody tr").length;
      const emptyShown = document.querySelector("#emptyState")?.hidden === false;
      const hasStorage = Boolean(localStorage.getItem("task-dashboard-data"));
      return rows > 0 || emptyShown || hasStorage;
    },
    { timeout: 5000 }
  );
}

async function readTasks(page) {
  return page.evaluate(
    ({ STORAGE_KEY }) => {
      const rows = Array.from(document.querySelectorAll("#taskTableBody tr"));

      const fromStorage = () => {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;

        try {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            return parsed.map((task) => ({
              id: task.id,
              name: task.name || "",
              creator: task.creator || "",
              createdAt: task.createdAt || "",
              status: task.status || "",
            }));
          }
        } catch {
          return null;
        }
        return null;
      };

      const fromDom = () =>
        rows.map((row) => ({
          name: row.querySelector(".task-name")?.textContent?.trim() || "",
          creator: row.querySelector(".creator")?.textContent?.trim() || "",
          createdAt: row.querySelector(".created-at")?.textContent?.trim() || "",
          status: row.querySelector(".status-select")?.value || "",
        }));

      return fromStorage() || fromDom();
    },
    { STORAGE_KEY }
  );
}

export async function listTasks({ keyword = "", field = "any", headless = true } = {}) {
  const searchFields = getSearchFields(field);
  const { context, page } = await launchBrowser({ headless });

  try {
    await page.goto(TASK_PAGE_URL, { waitUntil: "domcontentloaded" });
    await waitForTaskTable(page);

    const tasks = await readTasks(page);
    const filtered = tasks.filter((task) =>
      searchFields.some((fieldName) => normalize(task[fieldName]).includes(normalize(keyword)))
    );

    return {
      count: filtered.length,
      tasks: filtered,
      message: filtered.length > 0 ? "ok" : "no matching task",
    };
  } finally {
    await context.close().catch(() => {});
  }
}

export async function updateTaskStatus({ keyword, fromStatus, toStatus, field = "any", headless = true }) {
  if (!keyword) {
    throw new Error("keyword required");
  }

  if (!toStatus || !STATUS_OPTIONS.includes(toStatus)) {
    throw new Error(`invalid target status, allowed: ${STATUS_OPTIONS.join(", ")}`);
  }

  const searchFields = getSearchFields(field);
  const { context, page } = await launchBrowser({ headless });

  try {
    await page.goto(TASK_PAGE_URL, { waitUntil: "domcontentloaded" });
    await waitForTaskTable(page);

    const result = await page.evaluate(
      ({ keyword, fromStatus, toStatus, searchFields, STORAGE_KEY }) => {
        const normalize = (value) => String(value || "").trim().toLowerCase();
        const rows = Array.from(document.querySelectorAll("#taskTableBody tr"));
        const currentRaw = localStorage.getItem(STORAGE_KEY);
        let currentTasks = [];

        if (currentRaw) {
          try {
            const parsed = JSON.parse(currentRaw);
            if (Array.isArray(parsed)) currentTasks = parsed;
          } catch {
            currentTasks = [];
          }
        }

        let matched = 0;
        let updated = 0;
        const changedTasks = [];

        const nextTasks = currentTasks.length > 0 ? currentTasks.map((task) => ({ ...task })) : [];

        rows.forEach((row, index) => {
          const name = row.querySelector(".task-name")?.textContent?.trim() || "";
          const creator = row.querySelector(".creator")?.textContent?.trim() || "";
          const createdAt = row.querySelector(".created-at")?.textContent?.trim() || "";
          const select = row.querySelector(".status-select");
          const currentStatus = select?.value || "";
          const task = { name, creator, createdAt, status: currentStatus };

          const hitKeyword = searchFields.some((fieldName) => normalize(task[fieldName]).includes(normalize(keyword)));
          const hitFromStatus = fromStatus ? normalize(currentStatus) === normalize(fromStatus) : true;

          if (hitKeyword && hitFromStatus && select) {
            matched += 1;
            if (currentStatus !== toStatus) {
              select.value = toStatus;
              select.dispatchEvent(new Event("change", { bubbles: true }));
            }
            updated += 1;
            changedTasks.push({ ...task, status: toStatus });

            if (nextTasks[index]) {
              nextTasks[index] = { ...nextTasks[index], status: toStatus };
            }
          }
        });

        if (updated > 0 && nextTasks.length > 0) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(nextTasks));
        }

        return {
          matched,
          updated,
          tasks: changedTasks,
          message: updated > 0 ? "updated" : "no matching task",
        };
      },
      { keyword, fromStatus, toStatus, searchFields, STORAGE_KEY }
    );

    return result;
  } finally {
    await context.close().catch(() => {});
  }
}
