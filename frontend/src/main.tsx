import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PageShell from "./components/PageShell";
import XpTable from "./routes/XpTable";
import "./index.css";

// Tracer router: a single "/" route nested under the persistent PageShell chrome.
// Plan 01-05 extracts this to src/router.tsx and adds the remaining seven routes
// plus the catch-all.
const router = createBrowserRouter([
  {
    element: <PageShell />,
    children: [{ path: "/", element: <XpTable /> }],
  },
]);

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
