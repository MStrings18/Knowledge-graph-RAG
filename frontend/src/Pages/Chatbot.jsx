import { useState, useEffect, useRef } from "react";
import { Send, MessageSquare, Upload } from "lucide-react";
import { toast } from "react-toastify";
import api from "../Components/axios";

export default function Chatbot() {
  const [conversations, setConversations] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginData, setLoginData] = useState({ username: "", password: "" });
  const [pendingUserMessage, setPendingUserMessage] = useState("");
  const messagesEndRef = useRef(null);

  const userid = localStorage.getItem("userid");

  const isBusy = loading || uploading; // Disable all inputs/buttons when sending/uploading

  // Helper: dedupe threads
  const dedupeThreads = (threads) => {
    const map = new Map();
    threads.forEach((t) => map.set(t.thread_id, t));
    return Array.from(map.values());
  };

  /* -------------------- Fetching -------------------- */
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await api.get(`/threads/${userid}`);
        const data = response.data;
        console.log(data)
        if (Array.isArray(data.threads) && data.threads.length > 0) {
          setConversations(dedupeThreads(data.threads));
          setCurrentChatId(data.threads[0].thread_id);
          toast.success("✅ Chat history loaded");
        } else {
          toast.info("No previous chats found, start a new one!");
        }
      } catch (err) {
        console.error(err);
        toast.error("❌ Failed to fetch chat history");
      }
    };
    fetchHistory();
  }, [userid]);

  useEffect(() => {
    if (!currentChatId) return;
    const fetchCurrentHistory = async () => {
      try {
        const response = await api.get(`/history/${currentChatId}`);
        const data = response.data; 
        setConversations((prev) =>
          dedupeThreads(
            prev.map((chat) =>
              chat.thread_id === currentChatId
                ? { ...chat, messages: data.history || [] }
                : chat
            )
          )
        );
      } catch (err) {
        console.error(err);
        toast.error("❌ Failed to fetch chat history");
      }
    };
    fetchCurrentHistory();
  }, [currentChatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversations, currentChatId]);

  const currentChat = conversations.find((c) => c.thread_id === currentChatId);

  /* -------------------- Send Message -------------------- */
  const sendMessageToAPI = async (message) => {
    if (loading) return;
    setLoading(true);

    const userMessage = { sender: "user", message };
    setConversations((prev) =>
      prev.map((chat) =>
        chat.thread_id === currentChatId
          ? { ...chat, messages: [...(chat.messages || []), userMessage] }
          : chat
      )
    );

    try {
      const response = await api.post("/chat", {
        user_message: message,
        user_id: userid,
        thread_id: currentChatId,
      });

      const data = response.data;

      
      if (data.response.response === "Please log in to your insurance account first") {
        setPendingUserMessage(message);
        setShowLoginModal(true);
      }

      const botMessage = {
        sender: "bot",
        message: data.response?.response,
      };

      setConversations((prev) =>
        prev.map((chat) =>
          chat.thread_id === currentChatId
            ? { ...chat, messages: [...(chat.messages || []), botMessage] }
            : chat
        )
      );
    } catch (err) {
      console.error(err);
      toast.error("❌ Failed to send message: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    if (!input.trim()) {
      toast.error("⚠️ Please enter a message before sending.");
      return;
    }
    sendMessageToAPI(input);
    setInput("");
  };



  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !currentChatId) {
      toast.error("⚠️ Please start or select a chat before uploading.");
      return;
    }
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("thread_id", currentChatId);
      formData.append("file", file);

      const response = await api.post("/threads/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data", // important for FormData
        },
      });

      const data = response.data;
      const uploadMessage = {
        sender: "bot",
        message: `📂 Document "${data.file_name}" uploaded successfully.`,
      };

      setConversations((prev) =>
        prev.map((chat) =>
          chat.thread_id === currentChatId
            ? { ...chat, messages: [...(chat.messages || []), uploadMessage] }
            : chat
        )
      );

      toast.success("✅ File uploaded!");
    } catch (err) {
      console.error(err);
      toast.error("❌ Failed to upload file");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  /* -------------------- New Chat -------------------- */
  const handleNewChat = async () => {
    try {
      const response = await api.post("/threads", { user_id: userid });
      const data = response.data;

      console.log(data)

      if (data.thread_id) {
        const newChat = { thread_id: data.thread_id, first_message: "", messages: [] };
        setConversations((prev) => [newChat, ...prev]);
        setCurrentChatId(data.thread_id);
        toast.success("✅ New chat started");
      } else {
        toast.error("❌ Could not create new chat");
      }
    } catch (err) {
      console.error(err);
      toast.error("❌ Failed to create new chat: " + err.message);
    }
  };

  /* -------------------- Login Submit -------------------- */
  const handleLoginSubmit = async () => {
    if (!loginData.username || !loginData.password) {
      toast.error("⚠️ Please fill both fields");
      return;
    }

    try {
      const res = await api.post("/insurance-login", {
        user_id: userid,
        thread_id: currentChatId,
        insurance_username: loginData.username,
        insurance_password: loginData.password,
      });
      console.log(res.data);

      if (res.data.status === "success") {
        setShowLoginModal(false);
        setLoginData({ username: "", password: "" });
        toast.success("✅ Logged in successfully");
        // Retry pending message
        if (pendingUserMessage) sendMessageToAPI(pendingUserMessage);
      } else {
        toast.error("❌ Login failed");
      }
    } catch (err) {
      console.error(err);
      toast.error("❌ Login failed: " + err.message);
    }
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-black text-gray-100">
      {/* Sidebar */}
      <div className="w-64 border-r border-gray-800 p-4 flex flex-col bg-gray-900/60 backdrop-blur-xl">
        <button
          onClick={handleNewChat}
          disabled={isBusy}
          className={`mb-4 p-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium shadow-lg hover:opacity-90 transition ${
            isBusy ? "opacity-50 cursor-not-allowed" : ""
          }`}
        >
          ➕ New Chat
        </button>
        <div className="flex-1 overflow-y-auto space-y-2">
          {conversations.map((chat) => (
            <div
              key={chat.thread_id}
              onClick={() => setCurrentChatId(chat.thread_id)}
              className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition ${
                chat.thread_id === currentChatId
                  ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md"
                  : "hover:bg-gray-800"
              }`}
            >
              <MessageSquare size={18} />
              <span className="truncate font-medium">
                {chat.first_message?.slice(0, 14) || "Untitled"}...
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Window */}
      <div className="flex flex-col flex-1">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {currentChat?.messages?.length ? (
            currentChat.messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"} animate-fadeIn`}
              >
                <div
                  className={`relative px-4 py-3 max-w-lg break-words text-sm sm:text-base rounded-2xl shadow-md transition ${
                    msg.sender === "user"
                      ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-br-none"
                      : "bg-gray-800/90 text-gray-200 border border-gray-700 rounded-bl-none"
                  }`}
                >
                  {msg.message}
                  <span
                    className={`absolute bottom-0 w-3 h-3 ${
                      msg.sender === "user"
                        ? "right-0 bg-gradient-to-r from-indigo-500 to-purple-600 clip-path-triangle-r"
                        : "left-0 bg-gray-800/90 border-l border-b border-gray-700 clip-path-triangle-l"
                    }`}
                  ></span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-gray-500 text-center mt-6">
              Start a new chat to see messages ✨
            </div>
          )}
          <div ref={messagesEndRef}></div>
        </div>

        {/* Input */}
        <div className="border-t border-gray-800 p-4 bg-gray-900/70 backdrop-blur-xl flex items-center gap-3">
          <textarea
            rows="1"
            className="flex-1 resize-none rounded-xl p-3 bg-gray-800 text-gray-100 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/70 disabled:opacity-50 transition"
            placeholder="Type a message..."
            value={input}
            disabled={isBusy}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())
            }
          />
          <label
            className={`p-3 rounded-xl bg-gradient-to-r from-green-600 to-emerald-500 text-white cursor-pointer hover:opacity-90 transition ${
              isBusy ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            <Upload size={20} />
            <input type="file" hidden onChange={handleUpload} disabled={isBusy} />
          </label>
          <button
            onClick={handleSend}
            disabled={isBusy}
            className={`p-3 rounded-xl transition ${
              isBusy
                ? "bg-gray-700 cursor-not-allowed"
                : "bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90 shadow-lg"
            }`}
          >
            {loading ? "..." : <Send size={20} />}
          </button>
        </div>
      </div>

      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/70 backdrop-blur-sm z-50">
          <div className="bg-gray-900/90 p-6 rounded-2xl w-96 shadow-2xl border border-gray-700">
            <h2 className="text-xl font-bold text-white mb-4">🔐 Login Required</h2>
            <input
              type="text"
              placeholder="Username"
              value={loginData.username}
              onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
              className="w-full p-3 mb-3 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
            <input
              type="password"
              placeholder="Password"
              value={loginData.password}
              onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
              className="w-full p-3 mb-4 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
            <button
              onClick={() => handleLoginSubmit()}
              className="w-full p-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 font-semibold text-white shadow-lg hover:opacity-90 transition"
            >
              Submit
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
