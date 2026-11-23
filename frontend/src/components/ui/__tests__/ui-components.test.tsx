import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Button } from "../Button";
import { Badge } from "../Badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "../Card";
import { Alert } from "../Alert";
import { Input } from "../Input";
import { Textarea } from "../Textarea";
import { Spinner } from "../Spinner";

describe("UI Foundation Components", () => {
  describe("Button", () => {
    it("renders children and handles click", () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click Me</Button>);

      const btn = screen.getByRole("button", { name: "Click Me" });
      expect(btn).toBeInTheDocument();
      fireEvent.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("displays spinner and is disabled when isLoading", () => {
      render(<Button isLoading>Processing</Button>);
      const btn = screen.getByRole("button", { name: "Processing" });
      expect(btn).toBeDisabled();
      expect(btn.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("applies primary and danger variant classes", () => {
      const { rerender } = render(<Button variant="primary">Primary</Button>);
      expect(screen.getByRole("button")).toHaveClass("bg-terminal-primary");

      rerender(<Button variant="danger">Danger</Button>);
      expect(screen.getByRole("button")).toHaveClass("bg-terminal-error");
    });
  });

  describe("Badge", () => {
    it("renders variant styling and status dot", () => {
      render(
        <Badge variant="success" withDot data-testid="success-badge">
          Completed
        </Badge>
      );
      const badge = screen.getByTestId("success-badge");
      expect(badge).toHaveTextContent("Completed");
      expect(badge).toHaveClass("bg-[#5BCB8A]/15");
      expect(badge.querySelector(".rounded-full")).toBeInTheDocument();
    });
  });

  describe("Card", () => {
    it("renders card subcomponents cleanly", () => {
      render(
        <Card data-testid="test-card">
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
            <CardDescription>Card Description</CardDescription>
          </CardHeader>
          <CardContent>Card Content Body</CardContent>
          <CardFooter>Card Footer</CardFooter>
        </Card>
      );

      expect(screen.getByText("Card Title")).toBeInTheDocument();
      expect(screen.getByText("Card Description")).toBeInTheDocument();
      expect(screen.getByText("Card Content Body")).toBeInTheDocument();
      expect(screen.getByText("Card Footer")).toBeInTheDocument();
    });
  });

  describe("Alert", () => {
    it("renders title, content, and appropriate role", () => {
      render(
        <Alert variant="warning" title="Warning Notice">
          Please verify configuration.
        </Alert>
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Warning Notice")).toBeInTheDocument();
      expect(screen.getByText("Please verify configuration.")).toBeInTheDocument();
    });
  });

  describe("Input & Textarea", () => {
    it("renders input with label and handles typing", () => {
      const handleChange = vi.fn();
      render(<Input label="Full Name" placeholder="Enter name" onChange={handleChange} />);

      expect(screen.getByLabelText("Full Name")).toBeInTheDocument();
      const input = screen.getByPlaceholderText("Enter name");
      fireEvent.change(input, { target: { value: "Jane Doe" } });
      expect(handleChange).toHaveBeenCalled();
    });

    it("displays error message on Input", () => {
      render(<Input label="Email" error="Invalid email format" />);
      expect(screen.getByText("Invalid email format")).toBeInTheDocument();
    });

    it("renders textarea with label and rows", () => {
      render(<Textarea label="Summary" rows={5} placeholder="Write summary" />);
      const textarea = screen.getByPlaceholderText("Write summary");
      expect(textarea).toHaveAttribute("rows", "5");
    });
  });

  describe("Spinner", () => {
    it("renders accessible loading label", () => {
      render(<Spinner label="Fetching data..." />);
      expect(screen.getByRole("status")).toBeInTheDocument();
      expect(screen.getAllByText("Fetching data...").length).toBeGreaterThan(0);
    });
  });
});

