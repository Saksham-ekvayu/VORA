/* eslint-disable react-refresh/only-export-components */
import { createAuthRoutes } from "../utils/routeFactory";
import {
  ForgotPassword,
  Login,
  Register,
  ResetPassword,
  VerifyEmail,
  VerifyOtp,
} from "../utils/routeImports";

const authRoutes = createAuthRoutes([
  { key: "login", path: "/auth/login", component: Login },
  { key: "register", path: "/auth/register", component: Register },
  {
    key: "forgot-password",
    path: "/auth/forgot-password",
    component: ForgotPassword,
  },
  {
    key: "reset-password",
    path: "/auth/reset-password",
    component: ResetPassword,
  },
  {
    key: "verify-email",
    path: "/auth/verify-email",
    component: VerifyEmail,
  },
  { key: "verify-otp", path: "/auth/verify-otp", component: VerifyOtp },
]);

export default authRoutes;
