import { createBrowserRouter } from "react-router";
import PageShell from "./components/PageShell";
import NotFoundPage from "./components/NotFoundPage";
import XpTable from "./routes/XpTable";
import Team from "./routes/Team";
import Fixtures from "./routes/Fixtures";
import Prices from "./routes/Prices";
import League from "./routes/League";
import Scoreboard from "./routes/Scoreboard";
import Differentials from "./routes/Differentials";
import Methodology from "./routes/Methodology";

/* Minimal placeholder until Task 2 wires in the real <ErrorState/>-backed
 * boundary. Deliberately per-route, never a single shared boundary on the
 * PageShell layout route above — a boundary there would unmount the header nav
 * along with the one page that failed (T-05-01). */
function ErrorFallback() {
  return <p>Something went wrong loading this page.</p>;
}

/* The 8 UI-SPEC routes plus the catch-all, in UI-SPEC "Routes" table order.
 * Exported separately from `router` so plan 01-05's Task 3 tests can rebuild the
 * identical tree with `createMemoryRouter` instead of duplicating it. */
export const routes = [
  {
    element: <PageShell />,
    children: [
      { path: "/", element: <XpTable />, errorElement: <ErrorFallback /> },
      { path: "/team", element: <Team />, errorElement: <ErrorFallback /> },
      { path: "/fixtures", element: <Fixtures />, errorElement: <ErrorFallback /> },
      { path: "/prices", element: <Prices />, errorElement: <ErrorFallback /> },
      { path: "/league", element: <League />, errorElement: <ErrorFallback /> },
      { path: "/scoreboard", element: <Scoreboard />, errorElement: <ErrorFallback /> },
      {
        path: "/differentials",
        element: <Differentials />,
        errorElement: <ErrorFallback />,
      },
      {
        path: "/methodology",
        element: <Methodology />,
        errorElement: <ErrorFallback />,
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
