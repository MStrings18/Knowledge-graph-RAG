// src/axios.js
import axios from "axios";

const api = axios.create({
  baseURL: "https://knowledge-graph-rag-proxy.onrender.com", // 🔹 Replace with your backend URL
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;
