// Global variables to hold fetched data
let portfolioData = {
  performance: { labels: [], values: [] },
  allocation: { labels: [], values: [], colors: [] },
  holdings: [],
  searchResults: [],
  transactions: [],
  summary: {},
};

// Pagination variables for search table
let currentPage = 1;
const recordsPerPage = 6;
let filteredResults = [...portfolioData.searchResults];

// Pagination variables for holdings table
let holdingsCurrentPage = 1;
let filteredHoldings = [...portfolioData.holdings];

let performanceChartInstance = null;
let allocationChartInstance = null;

// Real-time update interval
let realTimeUpdateInterval = null;

let isTransactionInProgress = false;

// --- API Interaction ---
const API_BASE_URL = "http://localhost:5001/api"; //

// Main function to initialize the application.
// It's called once the HTML document is fully loaded.
async function initializeApp() {
  setupEventListeners();
  await loadAllData(); // Fetch all data from backend and update the UI
  populateSearchTableWithHoldings();
  // startRealTimeUpdates(); // Start real-time updates
}

function setupEventListeners() {
  const searchInput = document.getElementById("searchInput");
  searchInput.addEventListener("input", handleSearchInput);
}

// Start real-time updates for stock prices
function startRealTimeUpdates() {
  // Clear any existing interval
  if (realTimeUpdateInterval) {
    clearInterval(realTimeUpdateInterval);
  }

  // Update every 5 minutes to avoid rate limiting
  realTimeUpdateInterval = setInterval(async () => {
    await updateRealTimeData();
  }, 300000); // 5 minutes in milliseconds
}

// Update real-time data (prices, changes, etc.)
async function updateRealTimeData() {
  if (isTransactionInProgress) {
    console.log("Transaction in progress, skipping real-time update.");
    return;
  }
  console.log("Fetching real-time updates...");
  try {
    const tables = document.querySelectorAll(".table-container");
    tables.forEach((table) => table.classList.add("price-updating"));

    // 1. Fetch holdings with updated, real-time prices from the SINGLE, CORRECT endpoint.
    // No more calling /holdings/realtime.
    const newHoldingsData = await fetchData("holdings");

    if (newHoldingsData) {
      // 2. Update local portfolio data
      portfolioData.holdings = newHoldingsData;
      filteredHoldings = [...newHoldingsData];

      // 3. Recalculate summary metrics on the client-side
      recalculateSummaryMetrics();

      // 4. Re-render the UI with updated data
      updateMetrics();
      populateHoldingsTable();
    }

    // 5. Refresh search results (popular or active query)
    const searchInput = document.getElementById("searchInput");
    const query = searchInput.value.trim();
    await fetchAndPopulateSearch(query, false); // false to not show loader

    setTimeout(() => {
      tables.forEach((table) => {
        table.classList.remove("price-updating");
        table.classList.add("price-updated");
      });
      setTimeout(
        () =>
          tables.forEach((table) => table.classList.remove("price-updated")),
        1000
      );
    }, 500);
  } catch (error) {
    console.error("Error updating real-time data:", error);
    const tables = document.querySelectorAll(".table-container");
    tables.forEach((table) => table.classList.remove("price-updating"));
  }
}

/**
 * Recalculates summary metrics based on the latest holdings data.
 */
function recalculateSummaryMetrics() {
  const totalStockValue = portfolioData.holdings.reduce(
    (sum, h) => sum + h.shares * h.currentPrice,
    0
  );
  const totalCostBasis = portfolioData.holdings.reduce(
    (sum, h) => sum + h.shares * h.avgPrice,
    0
  );

  const cashBalance = portfolioData.summary.cashBalance || 0;

  portfolioData.summary.totalPortfolioValue = totalStockValue + cashBalance;
  portfolioData.summary.totalGainLoss = totalStockValue - totalCostBasis;
  portfolioData.summary.totalHoldings = portfolioData.holdings.length;
}

async function fetchData(endpoint) {
  try {
    console.log(`Fetching: ${API_BASE_URL}/${endpoint}`);
    const response = await fetch(`${API_BASE_URL}/${endpoint}`);
    console.log(`Response status: ${response.status} for ${endpoint}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log(`Data received for ${endpoint}:`, data);
    return data;
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    return null; // Return null to indicate failure
  }
}

async function postData(endpoint, data) {
  try {
    const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.error || `HTTP error! status: ${response.status}`
      );
    }

    return await response.json();
  } catch (error) {
    // --- Enhanced Debugging ---
    console.error(`Detailed error in postData for ${endpoint}:`, error);
    // Check if it's a network/CORS issue
    if (error instanceof TypeError && error.message.includes("fetch")) {
      console.error("This looks like a network/CORS issue or incorrect URL.");
      // alert(`Network/CORS Error or Incorrect URL for ${endpoint}. Check browser console and backend CORS configuration.`);
    } else {
      console.error(`Error posting to ${endpoint}:`, error);
      // alert(`Action failed: ${error.message}`);
    }
    // --- End Enhanced Debugging ---
    return null;
  }
}

// --- Data Loading and Refresh ---
async function loadAllData() {
  const [performance, allocation, holdings, search, summary] =
    await Promise.all([
      fetchData("performance"),
      fetchData("allocation"),
      fetchData("holdings"),
      fetchData("search"),
      fetchData("summary"),
    ]);

  portfolioData.performance = performance || { labels: [], values: [] };
  portfolioData.allocation = allocation || {
    labels: [],
    values: [],
    colors: [],
  };
  portfolioData.holdings = holdings || [];
  portfolioData.searchResults = search || [];
  portfolioData.summary = summary || {};

  filteredHoldings = [...portfolioData.holdings];
  filteredResults = [...portfolioData.searchResults];

  updateUI();
}

//  A generic function to send a DELETE request.
//  @param {string} endpoint - The API endpoint to send the delete request to.
//  @returns {Promise<object|null>}

async function deleteData(endpoint) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "DELETE",
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `HTTP error! Status: ${response.status}`);
    }
    return result;
  } catch (error) {
    console.error(`Error deleting from ${endpoint}:`, error);
    alert(`Action failed: ${error.message}`);
    return null;
  }
}

/**
 * Refreshes the dashboard UI after a buy/sell transaction.
 * @param {object} newSummary - The new summary object from the backend response.
 */
async function refreshDashboardPostTransaction(newSummary) {
  // 1. Update the summary data object directly from the response
  if (newSummary) {
    portfolioData.summary = newSummary;
  }

  // 2. Fetch the updated holdings, performance, and allocation
  const [holdingsData, performanceData, allocationData] = await Promise.all([
    fetchData("holdings"),
    fetchData("performance"),
    fetchData("allocation"),
  ]);

  if (holdingsData) {
    portfolioData.holdings = holdingsData;
    filteredHoldings = [...holdingsData];
  }
  if (performanceData) portfolioData.performance = performanceData;
  if (allocationData) portfolioData.allocation = allocationData;

  // 3. Re-render the entire UI to reflect all changes
  updateUI();
}

function updateUI() {
  holdingsCurrentPage = 1; // Reset to first page
  currentPage = 1; // Reset search to first page
  // Update metrics (needs calculation based on new data)
  updateMetrics();
  // Update charts
  initializeCharts(); // This will redraw charts with new data
  // Update tables
  populateHoldingsTable();
  // Initialize search table with default data
  populateSearchTable(portfolioData.searchResults);
}

// --- Metrics Calculation ---
// function updateMetrics() {
//   // 1. Total Portfolio Value
//   let totalStockValue = 0;
//   portfolioData.holdings.forEach((holding) => {
//     totalStockValue += holding.shares * holding.currentPrice;
//   });
//   // Assuming static cash and bonds from allocation endpoint for simplicity
//   // In a full app, these might come from separate API calls or be part of holdings
//   const cashValue = 12450.0; // From your allocation logic
//   const bondsValue = 28447.0; // From your allocation logic
//   const totalPortfolioValue = totalStockValue + cashValue + bondsValue;
//   document.querySelector(
//     ".metric-card:nth-child(1) .metric-value"
//   ).textContent = `$${totalPortfolioValue.toLocaleString("en-US", {
//     minimumFractionDigits: 2,
//     maximumFractionDigits: 2,
//   })}`;

//   // 2. Total Gain/Loss
//   let totalGainLoss = 0;
//   let totalCostBasis = 0;
//   portfolioData.holdings.forEach((holding) => {
//     const currentValue = holding.shares * holding.currentPrice;
//     const costBasis = holding.shares * holding.avgPrice;
//     totalGainLoss += currentValue - costBasis;
//     totalCostBasis += costBasis;
//   });
//   // Add gain/loss from static assets if applicable (e.g., if they have yields)
//   // For now, we base gain/loss purely on stock holdings
//   const totalGainLossPercent =
//     totalCostBasis > 0
//       ? ((totalGainLoss / totalCostBasis) * 100).toFixed(2)
//       : "0.00";
//   document.querySelector(
//     ".metric-card:nth-child(2) .metric-value"
//   ).textContent = `${totalGainLoss >= 0 ? "+" : ""}$${Math.abs(
//     totalGainLoss
//   ).toLocaleString("en-US", {
//     minimumFractionDigits: 2,
//     maximumFractionDigits: 2,
//   })}`;
//   document.querySelector(
//     ".metric-card:nth-child(2) .metric-description"
//   ).textContent = `(${totalGainLossPercent}%) Since portfolio inception`;

//   // 3. Cash Balance (Static for now, could be dynamic)
//   document.querySelector(
//     ".metric-card:nth-child(3) .metric-value"
//   ).textContent = `$${cashValue.toLocaleString("en-US", {
//     minimumFractionDigits: 2,
//     maximumFractionDigits: 2,
//   })}`;

//   // 4. Total Holdings (Number of unique stock symbols held)
//   const totalHoldingsCount = portfolioData.holdings.length;
//   document.querySelector(
//     ".metric-card:nth-child(4) .metric-value"
//   ).textContent = totalHoldingsCount;
// }

function updateMetrics() {
  const { totalPortfolioValue, totalGainLoss, cashBalance, totalHoldings } =
    portfolioData.summary;

  document.querySelector(
    ".metric-card:nth-child(1) .metric-value"
  ).textContent = `$${(totalPortfolioValue || 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
  document.querySelector(
    ".metric-card:nth-child(2) .metric-value"
  ).textContent = `${(totalGainLoss || 0) >= 0 ? "+" : ""}$${Math.abs(
    totalGainLoss || 0
  ).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
  document.querySelector(
    ".metric-card:nth-child(3) .metric-value"
  ).textContent = `$${(cashBalance || 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
  document.querySelector(
    ".metric-card:nth-child(4) .metric-value"
  ).textContent = totalHoldings || 0;
}

// Initialize charts
function initializeCharts() {
  // Destroy existing performance chart
  if (performanceChartInstance) {
    performanceChartInstance.destroy();
  }
  // Performance Chart
  const performanceCtx = document
    .getElementById("performanceChart")
    .getContext("2d");
  performanceChartInstance = new Chart(performanceCtx, {
    type: "line",
    data: {
      labels: portfolioData.performance.labels,
      datasets: [
        {
          label: "Portfolio Value",
          data: portfolioData.performance.values,
          borderColor: "#4285f4",
          backgroundColor: "rgba(66, 133, 244, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        x: {
          grid: {
            color: "rgba(0, 0, 0, 0.1)",
          },
          ticks: {
            color: "#6c757d",
          },
        },
        y: {
          grid: {
            color: "rgba(0, 0, 0, 0.1)",
          },
          ticks: {
            color: "#6c757d",
            callback: function (value) {
              return "$" + value / 1000 + "k";
            },
          },
        },
      },
    },
  });
  // Destroy existing allocation chart
  if (allocationChartInstance) {
    allocationChartInstance.destroy();
  }

  // Allocation Chart
  const allocationCtx = document
    .getElementById("allocationChart")
    .getContext("2d");
  allocationChartInstance = new Chart(allocationCtx, {
    type: "doughnut",
    data: {
      labels: portfolioData.allocation.labels,
      datasets: [
        {
          data: portfolioData.allocation.values,
          backgroundColor: portfolioData.allocation.colors,
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#495057",
            padding: 20,
          },
        },
      },
    },
  });
}

// Populate holdings table with pagination
function populateHoldingsTable() {
  const tbody = document.getElementById("holdingsTableBody");
  tbody.innerHTML = "";

  const paginatedHoldings = getPaginatedData(
    filteredHoldings,
    holdingsCurrentPage,
    recordsPerPage
  );

  paginatedHoldings.forEach((holding) => {
    const currentValue = holding.shares * holding.currentPrice;
    const totalCost = holding.shares * holding.avgPrice;
    const gainLoss = currentValue - totalCost;
    const gainLossPercent = ((gainLoss / totalCost) * 100).toFixed(2);

    const row = document.createElement("tr");
    row.innerHTML = `
                  <td><strong>${holding.symbol}</strong><br><small>${
      holding.name
    }</small></td>
                  <td>${holding.shares}</td>
                  <td>$${holding.avgPrice.toFixed(2)}</td>
                  <td class="live-price">$${currentValue.toFixed(2)}</td>
                  <td class="${
                    gainLoss >= 0 ? "trend-positive" : "trend-negative"
                  }">
                      ${gainLoss >= 0 ? "+" : ""}$${gainLoss.toFixed(
      2
    )} (${gainLossPercent}%)
                  </td>
                  <td>
                      <button class="btn btn-danger" onclick="sellStock('${
                        holding.symbol
                      }', ${holding.shares})">Sell</button>
                  </td>
              `;
    tbody.appendChild(row);
  });

  updateHoldingsPaginationControls();
}

function updateHoldingsPaginationControls() {
  const totalPages = Math.ceil(filteredHoldings.length / recordsPerPage);
  let paginationContainer = document.getElementById("holdingsPagination");
  if (!paginationContainer) {
    const holdingsTableContainer = document.querySelector(
      ".tables-section .table-container:last-child"
    );
    const paginationDiv = document.createElement("div");
    paginationDiv.id = "holdingsPagination";
    paginationDiv.className = "pagination-controls mt-2";
    holdingsTableContainer.appendChild(paginationDiv);
    paginationContainer = document.getElementById("holdingsPagination");
  }
  paginationContainer.innerHTML = "";

  if (totalPages <= 1) return;

  const prevBtn = document.createElement("button");
  prevBtn.className = "btn btn-secondary btn-sm me-2";
  prevBtn.innerHTML = "← Previous";
  prevBtn.disabled = holdingsCurrentPage === 1;
  prevBtn.onclick = () => {
    if (holdingsCurrentPage > 1) {
      holdingsCurrentPage--;
      populateHoldingsTable();
    }
  };
  paginationContainer.appendChild(prevBtn);

  const pageInfo = document.createElement("span");
  pageInfo.className = "pagination-info mx-2";
  pageInfo.textContent = `Page ${holdingsCurrentPage} of ${totalPages}`;
  paginationContainer.appendChild(pageInfo);

  const nextBtn = document.createElement("button");
  nextBtn.className = "btn btn-secondary btn-sm ms-2";
  nextBtn.innerHTML = "Next →";
  nextBtn.disabled = holdingsCurrentPage === totalPages;
  nextBtn.onclick = () => {
    if (holdingsCurrentPage < totalPages) {
      holdingsCurrentPage++;
      populateHoldingsTable();
    }
  };
  paginationContainer.appendChild(nextBtn);
}

// Get paginated data
function getPaginatedData(data, page, recordsPerPage) {
  const startIndex = (page - 1) * recordsPerPage;
  const endIndex = startIndex + recordsPerPage;
  return data.slice(startIndex, endIndex);
}

// Update pagination controls
function updatePaginationControls() {
  const totalPages = Math.ceil(filteredResults.length / recordsPerPage);
  let paginationContainer = document.getElementById("searchPagination");

  if (!paginationContainer) {
    // Create pagination container if it doesn't exist
    const searchTableContainer = document.querySelector(
      ".tables-section .table-container:first-child"
    );
    const paginationDiv = document.createElement("div");
    paginationDiv.id = "searchPagination";
    paginationDiv.className = "pagination-controls";
    searchTableContainer.appendChild(paginationDiv);
    paginationContainer = document.getElementById("searchPagination");
  }

  paginationContainer.innerHTML = "";

  if (totalPages <= 1) {
    return; // Don't show pagination if only one page
  }

  // Previous button
  const prevBtn = document.createElement("button");
  prevBtn.className = "btn btn-secondary pagination-btn";
  prevBtn.innerHTML = "← Previous";
  prevBtn.disabled = currentPage === 1;
  prevBtn.onclick = () => {
    if (currentPage > 1) {
      currentPage--;
      populateSearchTable(filteredResults)
      updatePaginationControls();
    }
  };
  paginationContainer.appendChild(prevBtn);

  // Page info
  const pageInfo = document.createElement("span");
  pageInfo.className = "pagination-info";
  pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  paginationContainer.appendChild(pageInfo);

  // Next button
  const nextBtn = document.createElement("button");
  nextBtn.className = "btn btn-secondary pagination-btn";
  nextBtn.innerHTML = "Next →";
  nextBtn.disabled = currentPage === totalPages;
  nextBtn.onclick = () => {
    if (currentPage < totalPages) {
      currentPage++;
      populateSearchTable(filteredResults)
      updatePaginationControls();
    }
  };
  paginationContainer.appendChild(nextBtn);
}

// Add this helper function
function formatCurrency(value) {
  return `$${parseFloat(value).toFixed(2)}`;
}


// --- Search Logic ---
let searchTimeout;

function handleSearchInput(event) {
  const query = event.target.value.trim();

  // Clear any previous search timeout
	clearTimeout(searchTimeout);

  if (query.length === 0) {
    // If search is empty, show default popular stocks
    populateSearchTableWithHoldings();
		return;
  }

  if (query.length > 0) {
    searchTimeout = setTimeout(() => {
      fetchAndPopulateSearch(query);
    }, 300); // Debounce for 300ms
  }
}

async function fetchAndPopulateSearch(query) {
  try {
    // Show loading state
    const tbody = document.getElementById("searchTableBody");
    tbody.innerHTML =
      '<tr><td colspan="5" style="text-align: center; color: #666;">Searching...</td></tr>';

    const results = await fetchData(`search?q=${encodeURIComponent(query)}`);
    if (results && Array.isArray(results)) {
      // populateSearchTable(results);
      filteredResults = results;
    } else {
      filteredResults = [];
      // populateSearchTable([]);
    }

    currentPage = 1;
		populateSearchTable(filteredResults);

  } catch (error) {
    console.error("Search error:", error);
    filteredResults = [];
    populateSearchTable([]);
  }
}

function populateSearchTableWithHoldings() {
  const holdingsAsSearchResults = portfolioData.holdings.map((holding) => ({
    symbol: holding.symbol,
    name: holding.name,
    price: holding.currentPrice,
    change: calculateChange(holding.currentPrice, holding.avgPrice),
  }));
  filteredResults = holdingsAsSearchResults;
	currentPage = 1;
  populateSearchTable(filteredResults);
}

function calculateChange(currentPrice, openPrice) {
  if (openPrice === 0) return "N/A";
  const change = currentPrice - openPrice;
  const changePercent = (change / openPrice) * 100;
  const sign = change >= 0 ? "+" : "";
  return `${sign}${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`;
}

function populateSearchTable(results) {
  const tbody = document.getElementById("searchTableBody");
  tbody.innerHTML = "";

  if (!results || results.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = `<td colspan="5" style="text-align: center; color: #666;">No stocks found. Try searching for a different symbol.</td>`;
    tbody.appendChild(row);
    updatePaginationControls();
    return;
  }

  const paginatedResults = getPaginatedData(
    results,
    currentPage,
    recordsPerPage
  );

  paginatedResults.forEach((stock) => {
    const row = document.createElement("tr");
    row.className = "search-result-row";

    const price =
      typeof stock.price === "number" ? `$${stock.price.toFixed(2)}` : "N/A";
    const changeClass =
      stock.change && stock.change.startsWith("+")
        ? "trend-positive"
        : "trend-negative";
    const priceClass = typeof stock.price === "number" ? "live-price" : "";

    // Escape special characters in the onclick to prevent JS errors
    const escapedSymbol = stock.symbol.replace(/'/g, "\\'");
    const escapedName = stock.name.replace(/'/g, "\\'");

    row.innerHTML = `
              <td><strong>${stock.symbol}</strong></td>
              <td>${stock.name}</td>
              <td class="${priceClass}">${price}</td>
              <td class="${changeClass}">${stock.change || "N/A"}</td>
              <td><button class="btn btn-primary" onclick="openAddModal('${escapedSymbol}', '${escapedName}', ${
      stock.price || 0
    })">Add</button></td>
          `;
    tbody.appendChild(row);
  });

  // Update pagination controls
  updatePaginationControls();
}

// Update holdings pagination controls
function updateHoldingsPaginationControls() {
  const totalPages = Math.ceil(filteredHoldings.length / recordsPerPage);
  let paginationContainer = document.getElementById("holdingsPagination");

  if (!paginationContainer) {
    // Create pagination container if it doesn't exist
    const holdingsTableContainer = document.querySelector(
      ".tables-section .table-container:last-child"
    );
    const paginationDiv = document.createElement("div");
    paginationDiv.id = "holdingsPagination";
    paginationDiv.className = "pagination-controls";
    holdingsTableContainer.appendChild(paginationDiv);
    paginationContainer = document.getElementById("holdingsPagination");
  }

  paginationContainer.innerHTML = "";

  if (totalPages <= 1) {
    return; // Don't show pagination if only one page
  }

  // Previous button
  const prevBtn = document.createElement("button");
  prevBtn.className = "btn btn-secondary pagination-btn";
  prevBtn.innerHTML = "← Previous";
  prevBtn.disabled = holdingsCurrentPage === 1;
  prevBtn.onclick = () => {
    if (holdingsCurrentPage > 1) {
      holdingsCurrentPage--;
      populateHoldingsTable();
      updateHoldingsPaginationControls();
    }
  };
  paginationContainer.appendChild(prevBtn);

  // Page info
  const pageInfo = document.createElement("span");
  pageInfo.className = "pagination-info";
  pageInfo.textContent = `Page ${holdingsCurrentPage} of ${totalPages}`;
  paginationContainer.appendChild(pageInfo);

  // Next button
  const nextBtn = document.createElement("button");
  nextBtn.className = "btn btn-secondary pagination-btn";
  nextBtn.innerHTML = "Next →";
  nextBtn.disabled = holdingsCurrentPage === totalPages;
  nextBtn.onclick = () => {
    if (holdingsCurrentPage < totalPages) {
      holdingsCurrentPage++;
      populateHoldingsTable();
      updateHoldingsPaginationControls();
    }
  };
  paginationContainer.appendChild(nextBtn);
}

// Search functionality with pagination

// Action functions
// async function addStock(symbol) {
//   // alert(`Added ${symbol} to your portfolio!`);

//   const response = await postData("stock/add", { symbol: symbol });
//   if (response) {
//     alert(response.message);
//     // Refresh data after adding
//     await loadAllData(); // This will fetch new holdings/search and update UI
//   }
//   // In a real application, this would make an API call to add the stock
// }

// async function sellStock(symbol) {
//   if (confirm(`Are you sure you want to sell all shares of ${symbol}?`)) {
//     const response = await postData("stock/sell", { symbol: symbol });
//     if (response) {
//       alert(response.message);
//       // Refresh data after selling
//       await loadAllData(); // This will fetch new holdings/search and update UI
//     }
//   }
// }

// --- Sell Modal Logic ---
let symbolToSell = null;

function sellStock(symbol, maxShares) {
  symbolToSell = symbol;
  const modal = document.getElementById("sellModal");
  const modalTitle = document.getElementById("sellModalTitle");
  const quantityInput = document.getElementById("sellModalQuantity");

  modalTitle.textContent = `Sell ${symbol}`;
  quantityInput.value = 1;
  quantityInput.max = maxShares;

  modal.style.display = "flex";
}

function closeSellModal() {
  const modal = document.getElementById("sellModal");
  modal.style.display = "none";
  symbolToSell = null; // Clear the symbol
}

async function confirmSell() {
  if (!symbolToSell) return;

  const quantityInput = document.getElementById("sellModalQuantity");
  const shares = parseInt(quantityInput.value, 10);

  if (isNaN(shares) || shares <= 0) {
    alert("Please enter a valid number of shares to sell.");
    return;
  }

  if (shares > parseInt(quantityInput.max, 10)) {
    alert(`You cannot sell more shares than you own (${quantityInput.max}).`);
    return;
  }

  isTransactionInProgress = true;

  const response = await postData("stock/sell", {
    symbol: symbolToSell,
    shares: shares,
  });
  if (response) {
    alert(response.message);
    closeSellModal();
    await refreshDashboardPostTransaction(response.summary);
  }
  isTransactionInProgress = false;
}

// --- Buy/ADD Modal Logic ---
let symbolToBuy = null;
let stockToAdd = null;

function openAddModal(symbol, name, price) {
  symbolToBuy = symbol;
  stockToAdd = { symbol, name, price };

  const modal = document.getElementById("buyModal");
  const modalTitle = document.getElementById("buyModalTitle");
  const quantityInput = document.getElementById("buyModalQuantity");
  const modalDescription = modal.querySelector("p");

  modalTitle.textContent = `Buy/Add ${symbol}`;
  modalDescription.textContent = `Enter the number of shares to buy for ${name} ($${price.toFixed(
    2
  )} per share)`;
  quantityInput.value = 1;
  quantityInput.min = 1;
  quantityInput.max = 10000; // Set a reasonable max

  modal.style.display = "flex";
}

function closeBuyModal() {
  const modal = document.getElementById("buyModal");
  modal.style.display = "none";
  symbolToBuy = null;
  stockToAdd = null;
}

async function confirmBuy() {
  if (!symbolToBuy) return;

  const quantityInput = document.getElementById("buyModalQuantity");
  const shares = parseInt(quantityInput.value, 10);

  if (isNaN(shares) || shares <= 0) {
    alert("Please enter a valid number of shares to buy.");
    return;
  }

  if (shares > parseInt(quantityInput.max, 10)) {
    alert(`You cannot buy more than ${quantityInput.max} shares at once.`);
    return;
  }
  isTransactionInProgress = true;
  const response = await postData("stock/add", {
    symbol: symbolToBuy,
    shares: shares,
  });
  if (response) {
    alert(response.message);
    closeBuyModal();
    await refreshDashboardPostTransaction(response.summary);
  }
  isTransactionInProgress = false;
}

// Initialize the dashboard
document.addEventListener("DOMContentLoaded", async function () {
  await initializeApp();

  // Set up search input event listener
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", handleSearchInput);
  }

  // Set up modal event listeners
  const confirmBuyBtn = document.getElementById("confirmBuyBtn");
  if (confirmBuyBtn) {
    confirmBuyBtn.addEventListener("click", confirmBuy);
  }

  const confirmSellBtn = document.getElementById("confirmSellBtn");
  if (confirmSellBtn) {
    confirmSellBtn.addEventListener("click", confirmSell);
  }
});
