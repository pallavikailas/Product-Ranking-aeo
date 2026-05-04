/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export — required for the monolithic Fly.io deploy (FastAPI serves the built files)
  output: "export",
  trailingSlash: true,

  images: {
    // Next.js Image Optimization API is unavailable in static exports.
    // Company logos are loaded via plain <img> tags so this only silences
    // the "unoptimized" warning.
    unoptimized: true,
  },
};

export default nextConfig;
