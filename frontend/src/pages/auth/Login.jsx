/* eslint-disable react/prop-types */

import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/authContext/useAuth";
import { isAdmin } from "@/utils/commonUtils";
import { toast } from "sonner";
import { loginApi } from "@/services/authService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;
    setIsLoading(true);

    try {
      const response = await loginApi(formData.email, formData.password);
      login(response.data.user, response.data.token, response.data.tenantId);
      toast.dismiss();
      toast.success(response.message || "Login successful");

      // Role-based redirect
      if (isAdmin(response.data.user?.role)) {
        navigate("/admin-dashboard");
      } else {
        navigate("/dashboard");
      }
    } catch (error) {
      console.error(
        "Login error:",
        error.message || "Invalid email or password"
      );
      toast.dismiss();
      toast.error(error.message || "Invalid email or password");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md rounded border border-border bg-card p-8 shadow-lg animate-in fade-in duration-500">
      <Helmet>
        <title>VORA - Login</title>
      </Helmet>
      {/* Title */}
      <h1
        className="
            text-4xl
            font-bold
            bg-primary
            bg-clip-text text-transparent
            tracking-[-1px]
            leading-[1.2]
            mb-2
          "
      >
        Welcome Back
      </h1>

      <p className="text-muted-foreground mb-6">
        Sign in to your account to continue
      </p>

      {/* Form */}
      <form className="space-y-4" onSubmit={handleSubmit}>
        {/* Email */}
        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input
            id="email"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            placeholder="Enter your email"
            className="w-full mt-1"
          />
        </div>

        {/* Password */}
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            placeholder="Enter your password"
            className="w-full mt-1"
          />
        </div>

        {/* Button */}
        <Button
          size="lg"
          type="submit"
          disabled={isLoading}
          className="mt-2 w-full cursor-pointer"
        >
          {isLoading ? "Signing in..." : "LOGIN"}
        </Button>
      </form>

      {/* Footer */}
      <div className="mt-6 text-center text-sm">
        <div className="flex items-center justify-center gap-10">
          <Link
            to="/auth/forgot-password"
            className="font-medium text-primary hover:underline"
          >
            Forgot password?
          </Link>
          <Link
            to="/auth/verify-email"
            className="font-medium text-primary hover:underline"
          >
            Verify Email?
          </Link>
        </div>

        <div className="mt-3 text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link
            to="/auth/register"
            className="font-medium text-primary hover:underline"
          >
            Register
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Login;
