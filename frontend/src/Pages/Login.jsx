import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { useNavigate } from "react-router-dom";

export default function Login() {

  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {

    e.preventDefault();
    console.log("inside handle submit")
    try {
      const res = await fetch("http://192.168.0.100:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json()

      console.log(data);

      if (data.status === "success" && !data.detail) {
          toast.success("Login successful");
          localStorage.setItem("userid",data.user_id)
          setTimeout(() => navigate("/chatbot"), 1500); // go to login
        } else {
          localStorage.removeItem("userid")    
          toast.error(data.detail || "Signup failed ❌");
        }
    } catch (err) {
      console.log(err)
      localStorage.removeItem("userid")
      toast.error("Server error: " + err.message)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gray-900">
      <div className="w-full max-w-md rounded-2xl bg-gray-800 p-8 shadow-lg">
        <h2 className="mb-6 text-center text-2xl font-bold text-white">
          Chatbot Login
        </h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-gray-600 bg-gray-700 p-3 text-white placeholder-gray-400 focus:border-indigo-500 focus:outline-none"
              placeholder="Enter your username"
              required
            />
          </div>

          {/* Password with Eye Toggle */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-gray-600 bg-gray-700 p-3 pr-10 text-white placeholder-gray-400 focus:border-indigo-500 focus:outline-none"
                placeholder="Enter your password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="w-full rounded-lg bg-indigo-600 px-4 py-3 font-semibold text-white transition hover:bg-indigo-500"
          >
            Login
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-400">
          Don’t have an account?{" "}
          <a href="/signup" className="text-indigo-400 hover:underline">
            Sign up
          </a>
        </p>
      </div>

      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
}
