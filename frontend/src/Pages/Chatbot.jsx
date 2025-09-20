import { useState, useEffect, useRef } from "react";
import { Send, MessageSquare, Upload } from "lucide-react";
import { toast } from "react-toastify";

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

  const dedupeThreads = (threads) => {
    const map = new Map();
    threads.forEach((t) => map.set(t.thread_id, t));
    return Array.from(map.values());
  };

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`http://localhost:8000/threads/${userid}`);
        const data = await res.json();
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
        const res = await fetch(`http://localhost:8000/history/${currentChatId}`);
        const data = await res.json();
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

  const sendMessageToAPI = async (message, extraData = {}) => {
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
      const res = await fetch(`http://localhost:8000/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: message,
          user_id: userid,
          thread_id: currentChatId,
        }),
      });

      const data = await res.json();
      console.log("chat send")

      if (data.response.response === "Please log in to your insurance account first") {
        console.log("inside check")
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

  const handleLoginSubmit = async () => {
  if (!loginData.username || !loginData.password) {
    toast.error("⚠️ Please enter both username and password");
    return;
  }

  const username = loginData.username;
  const password = loginData.password;

  try {
    const res = await fetch(`http://localhost:8000/insurance-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userid,
        thread_id:currentChatId,
        insurance_username: username,
        insurance_password: password,
      }),
    });

    const data = await res.json();
    console.log(data)
    if (data.status === "success") {
      toast.success("✅ Login successful");

      // Close modal
      setShowLoginModal(false);

      // Send the pending message to chat API with credentials
      if (pendingUserMessage) {
        const messageToSend = pendingUserMessage;
        setPendingUserMessage(""); // prevent modal reopening

        /*
        sendMessageToAPI(messageToSend, {
          username,
          password,
        });
        */
        setLoginData({ username: "", password: "" });
      }
    } else {
      toast.error(data.detail || "❌ Login failed");
    }
  } catch (err) {
    console.error(err);
    toast.error("Server error: " + err.message);
  }
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

      const res = await fetch(`http://localhost:8000/threads/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();

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

  const handleNewChat = async () => {
    try {
      const res = await fetch(`http://localhost:8000/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userid }),
      });

      if (!res.ok) throw new Error("Failed to create new chat");
      const data = await res.json();
      console.log(data)

      if (data.thread_id) {
        const newChat = {
          thread_id: data.thread_id,
          first_message: "", // initially empty
          messages: [],
        };

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


  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <div className="w-64 border-r border-gray-700 p-4 flex flex-col bg-gray-800">
        <button
          onClick={handleNewChat}
          className="mb-4 p-2 bg-blue-600 rounded-lg hover:bg-blue-700 text-white w-full"
        >
          ➕ New Chat
        </button>
        <div className="flex-1 overflow-y-auto space-y-2">
          {conversations.map((chat) => (
            <div
              key={chat.thread_id}
              onClick={() => setCurrentChatId(chat.thread_id)}
              className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer ${
                chat.thread_id === currentChatId
                  ? "bg-blue-600 text-white"
                  : "hover:bg-gray-700"
              }`}
            >
              <MessageSquare size={18} />
              <span className="truncate">
                {chat.first_message?.slice(0, 10) || "Untitled"}...
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Window */}
      <div className="flex flex-col flex-1">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {currentChat?.messages?.length ? (
            currentChat.messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`px-4 py-2 rounded-2xl max-w-xs ${
                    msg.sender === "user"
                      ? "bg-blue-600 text-white rounded-br-none"
                      : "bg-gray-700 text-gray-100 rounded-bl-none"
                  }`}
                >
                  {msg.message}
                </div>
              </div>
            ))
          ) : (
            <div className="text-gray-400 text-center mt-4">
              Start a chat to see messages
            </div>
          )}
          <div ref={messagesEndRef}></div>
        </div>

        {/* Input */}
        <div className="border-t border-gray-700 p-3 bg-gray-800 flex items-center gap-2">
          <textarea
            rows="1"
            className="flex-1 resize-none border border-gray-600 rounded-lg p-2 bg-gray-900 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            placeholder="Type a message..."
            value={input}
            disabled={loading}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())
            }
          />
          <label className="p-2 rounded-lg bg-green-600 hover:bg-green-700 text-white cursor-pointer disabled:opacity-50">
            <Upload size={20} />
            <input
              type="file"
              hidden
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
          <button
            onClick={handleSend}
            disabled={loading}
            className={`p-2 rounded-lg ${
              loading ? "bg-gray-600 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700 text-white"
            }`}
          >
            {loading ? "..." : <Send size={20} />}
          </button>
        </div>
      </div>

      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
          <div className="bg-gray-900 p-6 rounded-lg w-80">
            <h2 className="text-white mb-4">Login Required</h2>
            <input
              type="text"
              placeholder="Username"
              value={loginData.username}
              onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
              className="w-full p-2 mb-3 rounded bg-gray-800 text-white"
            />
            <input
              type="password"
              placeholder="Password"
              value={loginData.password}
              onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
              className="w-full p-2 mb-3 rounded bg-gray-800 text-white"
            />
            <button
              onClick={handleLoginSubmit}
              className="w-full p-2 bg-blue-600 rounded hover:bg-blue-700 text-white"
            >
              Submit
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
