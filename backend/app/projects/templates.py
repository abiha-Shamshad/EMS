"""Kickoff project templates used by the Win action (spec Section 12): code constants, 12 / 15 / 0 tasks.
The spec fixes the template names and task counts; the task titles below are this implementation's defaults."""

TEMPLATES: dict[str, list[str]] = {
    "website_standard": [
        "Kickoff meeting", "Requirements and sitemap", "Content collection", "Wireframes", "Visual design",
        "Design review with client", "Front-end build", "CMS setup", "Forms and integrations", "QA and accessibility checks",
        "Launch", "Post-launch review",
    ],
    "mobile_app_standard": [
        "Kickoff meeting", "Requirements and user stories", "User flows", "Wireframes", "Visual design",
        "Design review with client", "API design", "Backend implementation", "App screens implementation",
        "Push notifications", "Analytics events", "QA on devices", "App store assets", "Store submission", "Post-launch review",
    ],
    "blank": [],
}
