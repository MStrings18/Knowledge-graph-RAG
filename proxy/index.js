import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import cors from "cors";

const app = express();

// Enable CORS for all routes
app.use(cors());

// Your GCP backend
const target = "http://34.66.255.153";

// Proxy all requests starting with /api
app.use(
  "/api",
  createProxyMiddleware({
    target,
    changeOrigin: true,
    pathRewrite: { "^/api": "" }, // removes /api before sending to backend
  })
);

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`Proxy running on port ${PORT}`);
});
