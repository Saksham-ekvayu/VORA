/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/authContext/useAuth";
import { resetPassword } from "@/services/authService";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import useOtpTimer from "@/hooks/useOtpTimer";

function ResetPassword() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    otp: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const { getEmailForVerification, clearPendingEmail } = useAuth();

  const email = getEmailForVerification();
  const { resendCooldown, isResendOtpLoading, handleResendOTP } =
    useOtpTimer(email);

  // Redirect if no email is pending
  useEffect(() => {
    if (!email) {
      navigate("/auth/forgot-password");
    }
  }, [email, navigate]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.newPassword !== formData.confirmPassword) {
      toast.error("New Password and Confirm Password do not match");
      return;
    }

    if (isLoading) return;
    setIsLoading(true);

    try {
      const response = await resetPassword({
        email,
        otp: formData.otp,
        password: formData.newPassword,
      });

      // Clear pending email
      clearPendingEmail();

      toast.success(
        response.message || "Password reset successful! Redirecting to login..."
      );

      // Navigate to login
      setTimeout(() => {
        navigate("/auth/login");
      }, 500);
    } catch (error) {
      console.error(
        error.message || "Failed to reset password. Please try again."
      );
      toast.error(
        error.message || "Failed to reset password. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md rounded border border-border bg-card p-8 shadow-lg animate-in fade-in duration-500">
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
        Reset Password
      </h1>

      <p className="text-muted-foreground mb-6">
        Enter the OTP sent to your email and create a new password
      </p>

      {/* Form */}
      <form className="space-y-5" onSubmit={handleSubmit}>
        {/* OTP */}
        <div className="space-y-2">
          <Label htmlFor="otp">Verification Code</Label>
          <Input
            type="text"
            id="otp"
            name="otp"
            value={formData.otp}
            onChange={handleChange}
            maxLength={6}
            required
            placeholder="Enter 6-digit OTP"
            className="w-full mt-1"
          />
          <p className="text-xs text-muted-foreground">OTP sent to {email}</p>
        </div>

        {/* New Password */}
        <div className="space-y-2">
          <Label htmlFor="newPassword">New Password</Label>
          <Input
            type="password"
            id="newPassword"
            name="newPassword"
            value={formData.newPassword}
            onChange={handleChange}
            required
            placeholder="Enter new password"
            className="w-full mt-1"
          />
          <p className="text-xs text-muted-foreground">
            Min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
          </p>
        </div>

        {/* Confirm Password */}
        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
            placeholder="Confirm new password"
            className="w-full mt-1"
          />
        </div>

        {/* Button */}
        <Button
          size="lg"
          type="submit"
          disabled={isLoading}
          className="mt-4 w-full cursor-pointer"
        >
          {isLoading ? "Resetting..." : "RESET PASSWORD"}
        </Button>
      </form>

      {/* Footer */}
      <div className="mt-6 space-y-3 text-center text-sm">
        <div className="text-muted-foreground">
          Didn&apos;t receive the code?{" "}
          {resendCooldown > 0 ? (
            <span className="text-muted-foreground">
              Resend in {resendCooldown}s
            </span>
          ) : (
            <button
              className={`font-medium text-primary ${
                isResendOtpLoading
                  ? "cursor-not-allowed opacity-60"
                  : "cursor-pointer hover:underline"
              }`}
              onClick={handleResendOTP}
              disabled={isResendOtpLoading}
            >
              {isResendOtpLoading ? "Resending..." : "Resend OTP"}
            </button>
          )}
        </div>

        <div className="flex justify-center gap-6">
          <Link
            to="/auth/login"
            className="font-medium text-primary hover:underline"
          >
            Back to Login
          </Link>
          <Link
            to="/auth/forgot-password"
            className="font-medium text-primary hover:underline"
          >
            Back to Forgot Password
          </Link>
        </div>
      </div>
    </div>
  );
}

export default ResetPassword;
