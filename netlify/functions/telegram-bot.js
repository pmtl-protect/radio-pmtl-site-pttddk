// ==========================================
// PHẦN 1: MAIN HANDLER (telegram-bot.js)
// Deploy file này vào: netlify/functions/telegram-bot.js
// ==========================================

exports.handler = async function (event, context) {
  // Chỉ chấp nhận POST request từ Telegram
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      body: "Method Not Allowed",
    };
  }

  try {
    const body = JSON.parse(event.body || "{}");

    if (body.message && body.message.text) {
      const chatId = body.message.chat.id;
      const text = body.message.text.trim();

      if (text === "/run") {
        await sendMessage(
          chatId,
          "⏳ Đang gửi lệnh kích hoạt workflow lên GitHub..."
        );

        await triggerGitHubAction(chatId);

      } else if (text === "/start") {

        await sendMessage(
          chatId,
          "👋 Bot đã chạy trên Netlify.\nGõ /run để chạy GitHub Actions."
        );

      } else {

        await sendMessage(
          chatId,
          "❓ Lệnh không hợp lệ.\nDùng /run để chạy workflow."
        );
      }
    }

    // Luôn trả về 200 cho Telegram
    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true }),
    };

  } catch (error) {

    console.error("Lỗi xử lý:", error);

    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true }),
    };
  }
};

// ==========================================
// PHẦN 2: CONFIG
// ==========================================

const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

// Thông tin GitHub Repo
const GITHUB_OWNER = process.env.GITHUB_OWNER; // ví dụ: username
const GITHUB_REPO = process.env.GITHUB_REPO;   // ví dụ: podcast-sync

// Tên file workflow trong .github/workflows/
const GITHUB_WORKFLOW_ID =
  process.env.GITHUB_WORKFLOW_ID || "sync.yml";

const TELEGRAM_API =
  `https://api.telegram.org/bot${TELEGRAM_TOKEN}`;

const GITHUB_API = "https://api.github.com";

// ==========================================
// PHẦN 3: GỬI TIN NHẮN TELEGRAM
// ==========================================

async function sendMessage(chatId, text) {

  try {

    await fetch(`${TELEGRAM_API}/sendMessage`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        chat_id: chatId,
        text: text,
      }),
    });

  } catch (error) {

    console.error("Lỗi gửi Telegram:", error);
  }
}

// ==========================================
// PHẦN 4: KÍCH HOẠT GITHUB ACTIONS
// ==========================================

async function triggerGitHubAction(chatId) {

  try {

    // API:
    // POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches

    const response = await fetch(
      `${GITHUB_API}/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${GITHUB_WORKFLOW_ID}/dispatches`,
      {
        method: "POST",

        headers: {
          Authorization: `Bearer ${GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
        },

		body: JSON.stringify({
		  ref: "main" 
		})
      }
    );

    if (response.ok) {

      await sendMessage(
        chatId,
        "✅ Đã gửi lệnh thành công!\nWorkflow đang chạy trên GitHub."
      );

    } else {

      const errText = await response.text();

      console.error("GitHub API Error:", errText);

      await sendMessage(
        chatId,
        `❌ Gửi lệnh thất bại.\n\n${errText}`
      );
    }

  } catch (error) {

    console.error("Lỗi trigger GitHub Actions:", error);

    await sendMessage(
      chatId,
      "❌ Có lỗi khi kích hoạt GitHub Workflow."
    );
  }
}
