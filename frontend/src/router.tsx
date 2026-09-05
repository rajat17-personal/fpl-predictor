import { createBrowserRouter } from "react-router";
import PageShell from "./components/PageShell";
import NotFoundPage from "./components/NotFoundPage";
import { RouteErrorBoundary } from "./components/ErrorState";
import XpTable from "./routes/XpTable";
import Team from "./routes/Team";
import Fixtures from "./routes/Fixtures";
import Prices from "./routes/Prices";
import League from "./routes/League";
import Scoreboard from "./routes/Scoreboard";
import Differentials from "./routes/Differentials";
import Methodology from "./routes/Methodology";

/* The 8 UI-SPEC routes plus the catch-all, in UI-SPEC "Routes" table order.
 * Each concrete route carries its OWN errorElement — never one shared boundary
 * on this layout route, which would take the header nav down along with a
 * failing page (T-05-01). Exported separately from `router` so plan 01-05's
 * Task 3 tests can rebuild the identical tree with `createMemoryRouter`
 * instead of duplicating it. */
export const routes = [
  {
    element: <PageShell />,
    children: [
      {
        path: "/",
        element: <XpTable />,
        errorElement: <RouteErrorBoundary resource="the xP table data" />,
      },
      {
        path: "/team",
        element: <Team />,
        errorElement: <RouteErrorBoundary resource="the team data" />,
      },
      {
        path: "/fixtures",
        element: <Fixtures />,
        errorElement: <RouteErrorBoundary resource="the fixtures data" />,
      },
      {
        path: "/prices",
        element: <Prices />,
        errorElement: <RouteErrorBoundary resource="the prices data" />,
      },
      {
        path: "/league",
        element: <League />,
        errorElement: <RouteErrorBoundary resource="the league data" />,
      },
      {
        path: "/scoreboard",
        element: <Scoreboard />,
        errorElement: <RouteErrorBoundary resource="the scoreboard data" />,
      },
      {
        path: "/differentials",
        element: <Differentials />,
        errorElement: <RouteErrorBoundary resource="the differentials data" />,
      },
      {
        path: "/methodology",
        element: <Methodology />,
        errorElement: <RouteErrorBoundary resource="the methodology page" />,
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
