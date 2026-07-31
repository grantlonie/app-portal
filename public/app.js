const grid = document.getElementById("app-grid");
const status = document.getElementById("status");

function renderApps(apps) {
  const fragment = document.createDocumentFragment();

  for (const app of apps) {
    const card = document.createElement("a");
    card.className = "card";
    card.href = app.url;
    card.rel = "noopener noreferrer";

    const icon = document.createElement("img");
    icon.className = "card-icon";
    icon.src = app.icon;
    icon.alt = "";
    icon.width = 48;
    icon.height = 48;

    const name = document.createElement("h2");
    name.className = "card-name";
    name.textContent = app.name;

    const description = document.createElement("p");
    description.className = "card-description";
    description.textContent = app.description;

    const cta = document.createElement("span");
    cta.className = "card-cta";
    cta.textContent = "Open";

    card.append(icon, name, description, cta);
    fragment.append(card);
  }

  grid.replaceChildren(fragment);
}

try {
  const response = await fetch("/apps.json", { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`Failed to load apps (${response.status})`);
  }
  const apps = await response.json();
  if (!Array.isArray(apps) || apps.length === 0) {
    status.hidden = false;
    status.textContent = "No apps configured yet.";
  } else {
    renderApps(apps);
  }
} catch (error) {
  status.hidden = false;
  status.textContent = "Could not load the app directory.";
  console.error(error);
}
