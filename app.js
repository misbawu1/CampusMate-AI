const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-input");
const resultsGrid = document.querySelector("#results");
const resultsTitle = document.querySelector("#results-title");
const resultsCount = document.querySelector("#resource-count");
const emptyState = document.querySelector("#empty-state");
const askForm = document.querySelector("#ask-form");
const askInput = document.querySelector("#ask-input");
const askButton = document.querySelector("#ask-button");
const askStatus = document.querySelector("#ask-status");
const askAnswer = document.querySelector("#ask-answer");

const icons = [
  { words: ["library", "book", "study", "research"], symbol: "✎", color: "#eee9fb", ink: "#7863b3", category: "Study & learning" },
  { words: ["tutor", "class", "homework", "math", "writing"], symbol: "✦", color: "#fff1dc", ink: "#c18a39", category: "Study & learning" },
  { words: ["health", "doctor", "wellness", "appointment"], symbol: "♡", color: "#ffedeb", ink: "#df827a", category: "Health & wellbeing" },
];

function getStyle(resource, index) {
  const text = `${resource.name} ${resource.description} ${resource.keywords.join(" ")}`.toLowerCase();
  return icons.find((icon) => icon.words.some((word) => text.includes(word))) || icons[index % icons.length];
}

function makeCard(resource, index) {
  const style = getStyle(resource, index);
  const card = document.createElement("article");
  card.className = "resource-card";
  card.style.animationDelay = `${index * 55}ms`;

  const top = document.createElement("div");
  top.className = "card-top";
  const icon = document.createElement("span");
  icon.className = "card-icon";
  icon.style.background = style.color;
  icon.style.color = style.ink;
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = style.symbol;
  const arrow = document.createElement("span");
  arrow.className = "card-arrow";
  arrow.setAttribute("aria-hidden", "true");
  arrow.textContent = "↗";
  top.append(icon, arrow);

  const category = document.createElement("span");
  category.className = "card-category";
  category.textContent = style.category;
  const title = document.createElement("h4");
  title.textContent = resource.name;
  const description = document.createElement("p");
  description.textContent = resource.description;
  const contact = document.createElement("a");
  contact.className = "card-contact";
  contact.href = `mailto:${encodeURIComponent(resource.contact)}`;
  contact.textContent = `Contact ${resource.name}  →`;

  card.append(top, category, title, description, contact);
  return card;
}

function renderResources(resources, query = "") {
  resultsGrid.replaceChildren(...resources.map(makeCard));
  resultsGrid.hidden = resources.length === 0;
  emptyState.hidden = resources.length !== 0;
  resultsCount.textContent = `${resources.length} ${resources.length === 1 ? "resource" : "resources"} to explore`;
  resultsTitle.textContent = query ? `Results for “${query}”` : "A good place to start";
}

async function startCampusMate() {
  try {
    const response = await fetch("knowledge.json");
    if (!response.ok) throw new Error("Campus information could not be loaded.");
    const resources = await response.json();
    renderResources(resources);

    function search(topic) {
      const query = topic.trim();
      if (!query) {
        renderResources(resources);
        return;
      }
      const needle = query.toLocaleLowerCase();
      const matches = resources.filter((resource) =>
        resource.name.toLocaleLowerCase().includes(needle)
        || resource.description.toLocaleLowerCase().includes(needle)
        || resource.keywords.some((word) => word.toLocaleLowerCase().includes(needle)),
      );
      renderResources(matches, query);
    }

    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      search(searchInput.value);
    });
    document.querySelectorAll("[data-topic]").forEach((button) => {
      button.addEventListener("click", () => {
        const topic = button.dataset.topic;
        searchInput.value = topic;
        search(topic);
      });
    });

    askForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = askInput.value.trim();
      if (!question) return;

      askButton.disabled = true;
      askStatus.textContent = "CampusMate is thinking…";
      askAnswer.hidden = true;
      askAnswer.textContent = "";

      try {
        const response = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
          body: JSON.stringify({ question }),
        });
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(result.error || "CampusMate couldn't answer right now.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          buffer += decoder.decode(value, { stream: !done });

          let eventBreak = buffer.indexOf("\n\n");
          while (eventBreak !== -1) {
            const eventText = buffer.slice(0, eventBreak);
            buffer = buffer.slice(eventBreak + 2);
            const dataLine = eventText.split("\n").find((line) => line.startsWith("data: "));
            if (dataLine) {
              const update = JSON.parse(dataLine.slice(6));
              if (update.type === "status") {
                askStatus.textContent = update.message;
              } else if (update.type === "text") {
                askAnswer.hidden = false;
                askAnswer.textContent += update.text;
                askStatus.textContent = "";
              } else if (update.type === "error") {
                throw new Error(update.message);
              } else if (update.type === "done") {
                askStatus.textContent = "";
              }
            }
            eventBreak = buffer.indexOf("\n\n");
          }

          if (done) break;
        }
      } catch (error) {
        askStatus.textContent = error.message || "CampusMate couldn't answer right now.";
      } finally {
        askButton.disabled = false;
      }
    });
  } catch (error) {
    resultsCount.textContent = "Resources unavailable";
    resultsGrid.hidden = true;
    emptyState.hidden = false;
    emptyState.textContent = "CampusMate couldn’t load its resource list. Refresh the page and try again.";
  } finally {
    resultsGrid.setAttribute("aria-busy", "false");
  }
}

startCampusMate();
