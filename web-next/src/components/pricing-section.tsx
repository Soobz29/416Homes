"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const tiers = [
  {
    name: "Basic",
    price: 99,
    description: "Perfect for testing the waters",
    features: [
      "Ken Burns photo transitions",
      "AI voiceover narration",
      "Background music",
      "40-60 second video",
      "HD resolution",
    ],
    cta: "Get Started",
    featured: false,
  },
  {
    name: "Cinematic",
    price: 249,
    description: "Most popular for serious sellers",
    features: [
      "Everything in Basic",
      "Veo 2.0 AI-generated clips",
      "Smooth camera movements",
      "Professional transitions",
      "Priority processing",
    ],
    cta: "Start Cinematic",
    featured: true,
  },
  {
    name: "Premium",
    price: 299,
    description: "Ultimate luxury experience",
    features: [
      "Everything in Cinematic",
      "AI photo enhancement",
      "Color grading",
      "Extended length (60-90s)",
      "Rush delivery (2-hour)",
    ],
    cta: "Go Premium",
    featured: false,
  },
] as const;

export function PricingSection() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">Choose Your Tier</h2>
          <p className="text-xl text-muted-foreground">
            Professional videos that sell properties faster
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={cn(
                "relative rounded-2xl border border-slate-800 bg-slate-900/40 p-6",
                tier.featured && "border-[#d4af37] border-2 shadow-lg scale-105"
              )}
            >
              {tier.featured && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-[#d4af37] to-[#b8941f] text-black px-4 py-1 rounded-full text-sm font-semibold">
                  Most Popular
                </div>
              )}

              <div className="mb-4">
                <h3 className="text-2xl font-semibold">{tier.name}</h3>
                <p className="text-muted-foreground mt-1">{tier.description}</p>
                <div className="mt-4">
                  <span className="text-4xl font-bold">${tier.price}</span>
                  <span className="text-muted-foreground"> CAD</span>
                </div>
              </div>

              <ul className="space-y-3 mb-6 text-sm">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <span className="h-5 w-5 text-[#d4af37]">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <Button
                variant={tier.featured ? "gold" : "outline"}
                className="w-full"
                onClick={() => handleSelectTier(tier.name.toLowerCase())}
              >
                {tier.cta}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function handleSelectTier(tier: string) {
  const orderForm = document.getElementById("order-form");
  if (orderForm) {
    orderForm.scrollIntoView({ behavior: "smooth" });
    const tierInput = document.getElementById("tier-input") as HTMLInputElement | null;
    if (tierInput) tierInput.value = tier;
  }
}

