// src/axios.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://10.82.77.192:8000", // 🔹 Replace with your backend URL
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;