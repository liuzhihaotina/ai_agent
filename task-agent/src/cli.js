import { listTasks, updateTaskStatus } from "./update.js";

function parseArgs(argv) {
  const args = {
    keyword: "",
    fromStatus: "",
    toStatus: "",
    field: "any",
    headless: true,
    mode: "update",
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--keyword" || arg === "-k") {
      args.keyword = argv[++i] || "";
    } else if (arg === "--from" || arg === "-f") {
      args.fromStatus = argv[++i] || "";
    } else if (arg === "--to" || arg === "-t") {
      args.toStatus = argv[++i] || "";
    } else if (arg === "--field") {
      args.field = argv[++i] || "any";
    } else if (arg === "--list") {
      args.mode = "list";
    } else if (arg === "--headed") {
      args.headless = false;
    }
  }

  return args;
}

async function main() {
  const args = parseArgs(process.argv);

  try {
    const result =
      args.mode === "list"
        ? await listTasks(args)
        : await updateTaskStatus(args);

    if (args.mode !== "list") {
      if (!args.keyword) {
        console.error(JSON.stringify({ error: "keyword required" }));
        process.exit(1);
      }

      if (!args.toStatus) {
        console.error(JSON.stringify({ error: "target status required" }));
        process.exit(1);
      }
    }
    process.stdout.write(
      JSON.stringify(
        {
          ...args,
          ...result,
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
