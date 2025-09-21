// src/axios.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://34.66.255.153", // 🔹 Replace with your backend URL
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;
