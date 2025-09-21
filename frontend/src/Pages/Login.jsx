import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { useNavigate } from "react-router-dom";
import api from "../Components/axios";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch("http://192.168.0.100:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()

      console.log(data);

      if (data.status === "success" && !data.detail) {
        toast.success("Login successful ✨");
        localStorage.setItem("userid", data.user_id);
        setTimeout(() => navigate("/chatbot"), 1500);
      } else {
        localStorage.removeItem("userid");
        toast.error(data.detail || "Login failed ❌");
      }
    } catch (err) {
      console.error(err);
      localStorage.removeItem("userid");
      toast.error("Server error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-black">
      <div className="w-full max-w-md rounded-3xl border border-gray-800/50 bg-gray-900/70 p-8 shadow-2xl backdrop-blur-xl">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 shadow-lg shadow-indigo-600/30">
            <span className="text-white text-2xl font-bold">AI</span>
          </div>
          <h2 className="text-3xl font-bold text-white">Welcome back</h2>
          <p className="mt-2 text-sm text-gray-400">
            Sign in to continue your journey 🚀
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Username */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-xl border border-gray-700 bg-gray-800/70 p-3 text-white placeholder-gray-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/70 focus:outline-none transition"
              placeholder="Enter your username"
              required
            />
          </div>

          {/* Password */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-gray-700 bg-gray-800/70 p-3 pr-10 text-white placeholder-gray-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/70 focus:outline-none transition"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-3 font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:opacity-90 active:scale-95 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-gray-400">
          Don’t have an account?{" "}
          <a
            href="/signup"
            className="text-indigo-400 hover:text-indigo-300 hover:underline transition"
          >
            Sign up
          </a>
        </p>
      </div>

      <ToastContainer position="top-right" autoClose={3000} theme="dark" />
    </div>
  );
}
