/* eslint-disable react/prop-types */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { register } from "@/services/authService";
import { useAuth } from "@/context/authContext/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import PhoneInputField from "@/components/custom/PhoneInputField";
import { isValidPhoneNumber } from "@/lib/phone";

function Register() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setEmailForVerification } = useAuth();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    // Basic validation
    if (!formData.name.trim()) {
      toast.error("Name is required");
      return;
    }
    if (!formData.email.trim()) {
      toast.error("Email is required");
      return;
    }
    if (!formData.password.trim()) {
      toast.error("Password is required");
      return;
    }
    if (formData.password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    // Phone number validation with toast
    if (!formData.phone) {
      toast.error("Phone number is required");
      return;
    }

    if (!isValidPhoneNumber(formData.phone)) {
      toast.error("Please enter a valid phone number");
      return;
    }

    try {
      setLoading(true);
      const payload = {
        ...formData,
        phone: formData.phone.replace(/^\+/, ""),
      };
      const response = await register(payload);

      if (response) {
        setEmailForVerification(formData.email);
        toast.success(
          "Registration successful! Please check your email for the verification code."
        );
        navigate("/auth/verify-otp");
      }
    } catch (error) {
      console.error("Registration error:", error);
      toast.error(error.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md rounded border border-border bg-card p-8 shadow-lg animate-in fade-in duration-500">
      <h1 className="text-4xl font-bold bg-primary bg-clip-text text-transparent tracking-[-1px] leading-[1.2] mb-2">
        Create Account
      </h1>
      <p className="text-muted-foreground mb-6">Join us to get started</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="Enter your name"
            disabled={loading}
            className="w-full mt-1"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email Address</Label>
          <Input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Enter your email"
            disabled={loading}
            className="w-full mt-1"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="phone">Phone Number</Label>
          <PhoneInputField
            id="phone"
            value={formData.phone}
            onChange={(val) => setFormData((prev) => ({ ...prev, phone: val }))}
            disabled={loading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Create a password"
            disabled={loading}
            className="w-full mt-1"
          />
        </div>

        <Button
          size="lg"
          type="submit"
          disabled={loading}
          className="mt-2 w-full cursor-pointer"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              Registering...
            </>
          ) : (
            "Register"
          )}
        </Button>
      </form>

      <div className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
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

export default Register;
