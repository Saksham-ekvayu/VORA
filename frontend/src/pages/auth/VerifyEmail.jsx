/* eslint-disable react/prop-types */

import { useState, useEffect } from "react";
import { Helmet } from "react-helmet-async";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/authContext/useAuth";
import { verifyEmail } from "@/services/authService";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function VerifyEmail() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ email: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const { getEmailForVerification, setEmailForVerification } = useAuth();

  const storedEmail = getEmailForVerification();

  // Set stored email in form data
  useEffect(() => {
    if (storedEmail) {
      setFormData({ email: storedEmail });
    }
  }, [storedEmail]);

  // Countdown timer for cooldown
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (cooldown > 0) {
      toast.error(`Please wait ${cooldown} seconds before requesting again.`);
      return;
    }

    if (isLoading) return;
    setIsLoading(true);

    try {
      const response = await verifyEmail(formData.email);

      // Store email for verification
      setEmailForVerification(formData.email);

      toast.success(
        response.message || "OTP sent successfully! Check your email."
      );
      setCooldown(60); // 60 second cooldown

      // Navigate to verify OTP
      navigate("/auth/verify-otp");
    } catch (error) {
      console.error(error.message || "Failed to send OTP. Please try again.");
      toast.error(error.message || "Failed to send OTP. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const getButtonText = () => {
    if (cooldown > 0) return `WAIT ${cooldown}s`;
    if (isLoading) return "Sending...";
    return "SEND OTP";
  };

  return (
    <div className="w-full max-w-md rounded border border-border bg-card p-8 shadow-lg animate-in fade-in duration-500">
      <Helmet>
        <title>VORA - Verify Email</title>
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
        Verify Email
      </h1>

      <p className="text-muted-foreground mb-8">
        Enter your email address to receive a new verification code
      </p>

      {/* Form */}
      <form className="space-y-6" onSubmit={handleSubmit}>
        {/* Email */}
        <div className="space-y-2">
          <Label htmlFor="email">Email Address</Label>
          <Input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            placeholder="Enter your email"
            className="w-full mt-1"
          />
        </div>

        {/* Button */}
        <Button
          size="lg"
          type="submit"
          disabled={isLoading || cooldown > 0}
          className="mt-2 w-full cursor-pointer"
        >
          {getButtonText()}
        </Button>
      </form>

      {/* Footer */}
      <div className="mt-8 text-center text-sm text-muted-foreground">
        Remember your password?{" "}
        <Link
          to="/auth/login"
          className="font-medium text-primary hover:underline"
        >
          Login here
        </Link>
      </div>
    </div>
  );
}

export default VerifyEmail;
