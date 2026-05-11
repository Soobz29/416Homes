export type TourShowcaseKind = "photo" | "walkthrough" | "scan";

export interface TourShowcaseItem {
  id: string;
  kind: TourShowcaseKind;
  badge: string;
  title: string;
  location: string;
  summary: string;
  previewImage: string;
  href: string;
  cta: string;
  detail: string;
}

export const TOUR_SHOWCASE_ITEMS: TourShowcaseItem[] = [
  {
    id: "demo-3d-tour",
    kind: "walkthrough",
    badge: "3D walkthrough demo",
    title: "Hosted 3D Showcase",
    location: "Matterport sample tour",
    summary:
      "A full-screen walkthrough demo that shows the immersive shell and navigation style we want 416Homes tours to ship with.",
    previewImage:
      "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1600&auto=format&fit=crop",
    href: "/tours/demo-3d-tour",
    cta: "Open 3D Demo →",
    detail: "Use this when you already have a scan or hosted 3D model.",
  },
  {
    id: "demo-photo-tour",
    kind: "photo",
    badge: "Photo tour demo",
    title: "Room-by-Room Listing Tour",
    location: "King West sample listing",
    summary:
      "A fast hosted tour built from normal listing photos. Rooms are grouped automatically and published to a shareable tour URL.",
    previewImage:
      "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1600&auto=format&fit=crop",
    href: "/tours/demo-photo-tour",
    cta: "Open Photo Demo →",
    detail: "Best for listings that only have standard listing photos.",
  },
  {
    id: "launch-beta",
    kind: "scan",
    badge: "Early access",
    title: "Bring Your Own 3D Scan",
    location: "Luma · Polycam · .splat",
    summary:
      "Upload a native splat file or paste a supported 3D tour link. We host it inside the 416Homes viewer and give you a shareable link.",
    previewImage:
      "https://images.unsplash.com/photo-1511818966892-d7d671e672a2?w=1600&auto=format&fit=crop",
    href: "/tours#order",
    cta: "Start a 3D Tour →",
    detail: "Current beta supports share links and .splat, .ply, or .ksplat uploads.",
  },
];
