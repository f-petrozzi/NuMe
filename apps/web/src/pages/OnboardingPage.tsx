import axios from "axios";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { refreshSessionUser, submitOnboarding } from "@/lib/api";
import type { OnboardingRequestDto } from "@/lib/api-contracts";
import { appConfig } from "@/lib/config";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Heart, ArrowRight, GraduationCap, HandHeart, User, Accessibility, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { useToast } from "@/hooks/use-toast";

const personas = [
  { id: "student", label: "Student", desc: "Academic stress, deadlines, and routine disruption", icon: GraduationCap },
  { id: "caregiver", label: "Caregiver", desc: "High-burden care responsibilities and burnout risk", icon: HandHeart },
  { id: "older_adult", label: "Older Adult", desc: "Routine support, readability, and low-complexity guidance", icon: User },
  { id: "accessibility_focused", label: "Accessibility", desc: "Low-energy, simplified, adaptive support planning", icon: Accessibility },
] as const;

const ageRanges = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"];
const sexOptions = ["female", "male", "non_binary", "prefer_not_to_say"];
const goalOptions = [
  { value: "stress_reduction", label: "Stress Reduction" },
  { value: "better_sleep", label: "Better Sleep" },
  { value: "weight_loss", label: "Weight Loss" },
  { value: "energy_improvement", label: "Energy Improvement" },
  { value: "burnout_recovery", label: "Burnout Recovery" },
] as const;
const activityLevels = ["low", "moderate", "high"];
const dietaryStyles = ["omnivore", "vegetarian", "vegan", "pescatarian", "gluten_free"];

const defaultForm: OnboardingRequestDto = {
  age_range: "",
  sex: "",
  height_cm: undefined,
  weight_kg: undefined,
  goal: "stress_reduction",
  activity_level: "moderate",
  dietary_style: "omnivore",
  allergies: [],
  persona_type: "student",
  simplified_language: false,
  large_text: false,
  low_energy_mode: false,
};

export default function OnboardingPage() {
  const [form, setForm] = useState<OnboardingRequestDto>(defaultForm);
  const [allergiesText, setAllergiesText] = useState("");
  const [loading, setLoading] = useState(false);
  const { user: authUser, setUser } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const updateForm = <K extends keyof OnboardingRequestDto>(field: K, value: OnboardingRequestDto[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const canSubmit = Boolean(form.persona_type && form.age_range && form.sex && form.goal);

  const handleSubmit = async () => {
    if (!canSubmit) return;

    setLoading(true);
    try {
      const payload: OnboardingRequestDto = {
        ...form,
        allergies: allergiesText
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      };

      const user = appConfig.useMockApi
        ? {
            ...(authUser ?? {
              id: "pending",
              email: "",
              full_name: "NüMe User",
              role: "member" as const,
            }),
            persona: payload.persona_type,
            onboarded: true,
          }
        : await submitOnboarding(payload);

      setUser(user);
      navigate("/dashboard");
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        try {
          const user = await refreshSessionUser(authUser?.full_name);
          setUser(user);
          navigate("/dashboard");
          return;
        } catch {
          // Fall through to the generic toast below if canonical refresh fails.
        }
      }

      const description = axios.isAxiosError(error)
        ? error.response?.data?.detail || "We couldn't save your profile just yet."
        : "We couldn't save your profile just yet.";

      toast({
        title: "Onboarding failed",
        description,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background px-6 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mx-auto w-full max-w-5xl">
        <div className="mb-10 flex items-center gap-2">
          <Heart className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold tracking-tight">NüMe</span>
        </div>

        <div className="mb-8">
          <h1 className="text-3xl font-bold">Build your care profile</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            This gives the care coordination system the context it needs to personalize recommendations, accessibility preferences, and support routing.
          </p>
        </div>

        <div className="space-y-8">
          <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
            <Label className="mb-4 block text-sm font-semibold">Which experience best matches you?</Label>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              {personas.map((persona) => (
                <button
                  key={persona.id}
                  type="button"
                  onClick={() => updateForm("persona_type", persona.id)}
                  className={`rounded-xl border-2 p-4 text-left transition-all ${
                    form.persona_type === persona.id
                      ? "border-primary bg-accent shadow-glow"
                      : "border-border bg-background hover:border-primary/40"
                  }`}
                >
                  <persona.icon className={`mb-3 h-5 w-5 ${form.persona_type === persona.id ? "text-primary" : "text-muted-foreground"}`} />
                  <p className="font-medium">{persona.label}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{persona.desc}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Profile Basics</h2>
              <p className="text-sm text-muted-foreground">Required profile data from the current architecture contract.</p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label>Age Range</Label>
                <Select value={form.age_range} onValueChange={(value) => updateForm("age_range", value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select age range" />
                  </SelectTrigger>
                  <SelectContent>
                    {ageRanges.map((age) => (
                      <SelectItem key={age} value={age}>{age}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Sex</Label>
                <Select value={form.sex} onValueChange={(value) => updateForm("sex", value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select sex" />
                  </SelectTrigger>
                  <SelectContent>
                    {sexOptions.map((option) => (
                      <SelectItem key={option} value={option}>{option.replace(/_/g, " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Primary Goal</Label>
                <Select value={form.goal} onValueChange={(value) => updateForm("goal", value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a goal" />
                  </SelectTrigger>
                  <SelectContent>
                    {goalOptions.map((goal) => (
                      <SelectItem key={goal.value} value={goal.value}>{goal.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="height_cm">Height (cm)</Label>
                <Input
                  id="height_cm"
                  type="number"
                  min="0"
                  placeholder="175"
                  value={form.height_cm ?? ""}
                  onChange={(event) => updateForm("height_cm", event.target.value ? Number(event.target.value) : undefined)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="weight_kg">Weight (kg)</Label>
                <Input
                  id="weight_kg"
                  type="number"
                  min="0"
                  placeholder="70"
                  value={form.weight_kg ?? ""}
                  onChange={(event) => updateForm("weight_kg", event.target.value ? Number(event.target.value) : undefined)}
                />
              </div>

              <div className="space-y-2">
                <Label>Activity Level</Label>
                <Select value={form.activity_level} onValueChange={(value) => updateForm("activity_level", value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select activity level" />
                  </SelectTrigger>
                  <SelectContent>
                    {activityLevels.map((level) => (
                      <SelectItem key={level} value={level}>{level}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label>Dietary Style</Label>
                <Select value={form.dietary_style} onValueChange={(value) => updateForm("dietary_style", value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select dietary style" />
                  </SelectTrigger>
                  <SelectContent>
                    {dietaryStyles.map((style) => (
                      <SelectItem key={style} value={style}>{style.replace(/_/g, " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 lg:col-span-3">
                <Label htmlFor="allergies">Allergies</Label>
                <Input
                  id="allergies"
                  placeholder="Comma-separated, e.g. peanuts, shellfish"
                  value={allergiesText}
                  onChange={(event) => setAllergiesText(event.target.value)}
                />
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Accessibility Preferences</h2>
              <p className="text-sm text-muted-foreground">These are optional now, but part of the target architecture and agent routing context.</p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <PreferenceToggle
                checked={form.simplified_language}
                label="Simplified language"
                description="Use shorter, lower-complexity explanations."
                onCheckedChange={(checked) => updateForm("simplified_language", checked)}
              />
              <PreferenceToggle
                checked={form.large_text}
                label="Large text"
                description="Prefer more readable, larger interface text."
                onCheckedChange={(checked) => updateForm("large_text", checked)}
              />
              <PreferenceToggle
                checked={form.low_energy_mode}
                label="Low energy mode"
                description="Favor low-step, lower-burden recommendations."
                onCheckedChange={(checked) => updateForm("low_energy_mode", checked)}
              />
            </div>
          </section>

          <Button onClick={handleSubmit} className="w-full" size="lg" disabled={!canSubmit || loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Continue to dashboard
            {!loading ? <ArrowRight className="ml-2 h-4 w-4" /> : null}
          </Button>
        </div>
      </motion.div>
    </div>
  );
}

function PreferenceToggle({
  checked,
  label,
  description,
  onCheckedChange,
}: {
  checked: boolean;
  label: string;
  description: string;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-background p-4 transition-colors hover:border-primary/30">
      <Checkbox checked={checked} onCheckedChange={(value) => onCheckedChange(value === true)} className="mt-0.5" />
      <div>
        <p className="font-medium">{label}</p>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </label>
  );
}
