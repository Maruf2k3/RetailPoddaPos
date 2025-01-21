/**********************************************
 * Global Variables
 **********************************************/
let orderItems = [];
let serverFilter = "All"; // default filter for the item list

/**********************************************
 * Open / Close Create/Edit Order Modal
 **********************************************/
function openOrderModal(mode, orderId = null) {
  const modalTitle = document.getElementById("modalTitle");

  if (mode === "edit") {
    modalTitle.innerText = "Edit Order";
    // Fetch existing order from the server
    fetch(`/order/${orderId}`)
      .then((response) => response.json())
      .then((data) => {
        document.getElementById("orderId").value = data.id;
        document.getElementById("tableNumber").value = data.table_number;
        document.getElementById("notes").value = data.notes || "";

        // Load items (uses 'qty' instead of 'quantity')
        orderItems = data.items || [];
        renderOrderSummary();
        updateGrandTotal();
        populateServerFilterSelect();

        document.getElementById("orderModal").classList.remove("hidden");
      })
      .catch((error) => {
        showMessage("Error fetching order data.", "error", true);
      });
  } else {
    modalTitle.innerText = "Create New Order";

    // Reset the form
    document.getElementById("orderForm").reset();
    document.getElementById("orderId").value = "";
    orderItems = [];

    renderOrderSummary();
    updateGrandTotal();
    populateServerFilterSelect();

    document.getElementById("orderModal").classList.remove("hidden");
  }
}

function closeOrderModal() {
  document.getElementById("orderModal").classList.add("hidden");
}

/**********************************************
 * Adding Items to the Order
 **********************************************/
function addItem(itemId, itemName, itemPrice) {
  // 1) Identify which server served this item
  const serverSelect = document.getElementById(`serverSelect${itemId}`);
  const servedBy = serverSelect ? serverSelect.value : "Unknown";

  // 2) Check if this (id, served_by) combo already exists
  const existingItem = orderItems.find(
    (item) => item.id === itemId && item.served_by === servedBy
  );

  if (existingItem) {
    existingItem.qty++;
  } else {
    // Include served_by in the object, and use 'qty'
    orderItems.push({
      id: itemId,
      name: itemName,
      price: parseFloat(itemPrice),
      qty: 1,
      served_by: servedBy,
    });
  }

  renderOrderSummary();
  updateGrandTotal();
  populateServerFilterSelect();
}

/**********************************************
 * Rendering Order Summary (with server filter)
 **********************************************/
function renderOrderSummary() {
  const orderSummary = document.getElementById("orderSummary");
  // Filter by server if user selected one
  const filteredItems =
    serverFilter === "All"
      ? orderItems
      : orderItems.filter((i) => i.served_by === serverFilter);

  if (filteredItems.length === 0) {
    orderSummary.innerHTML = `
      <tr>
        <td colspan="6" class="p-2 border text-center">No items added.</td>
      </tr>
    `;
    return;
  }

  orderSummary.innerHTML = filteredItems
    .map((item) => {
      const total = (item.qty * item.price).toFixed(2);
      return `
        <tr>
          <td class="p-2 border">${item.name}</td>
          <td class="p-2 border">
            <input
              type="number"
              min="1"
              value="${item.qty}"
              class="w-12 text-center border text-neutral-900 font-bold"
              onchange="updateItemQuantity('${item.id}', '${
        item.served_by
      }', this.value)"
            />
          </td>
          <td class="p-2 border">${item.price.toFixed(2)}</td>
          <td class="p-2 border">${item.served_by}</td>
          <td class="p-2 border">${total}</td>
          <td class="p-2 border">
            <button 
              onclick="removeItem('${item.id}', '${item.served_by}')"
              class="text-red-500"
            >
              Remove
            </button>
          </td>
        </tr>
      `;
    })
    .join("");
}

function populateServerFilterSelect() {
  const serverFilterSelect = document.getElementById("serverItemFilter");
  const uniqueServers = new Set(orderItems.map((i) => i.served_by));

  serverFilterSelect.innerHTML = "";

  // "All" option
  const allOption = document.createElement("option");
  allOption.value = "All";
  allOption.textContent = "All Servers";
  serverFilterSelect.appendChild(allOption);

  uniqueServers.forEach((serverName) => {
    const opt = document.createElement("option");
    opt.value = serverName;
    opt.textContent = serverName;
    serverFilterSelect.appendChild(opt);
  });

  serverFilterSelect.value = serverFilter;
}

function filterOrderItemsByServer() {
  serverFilter = document.getElementById("serverItemFilter").value;
  renderOrderSummary();
}

/**********************************************
 * Update or Remove Items
 **********************************************/
function updateItemQuantity(id, servedBy, newQty) {
  const qty = parseInt(newQty, 10);
  if (isNaN(qty) || qty <= 0) {
    removeItem(id, servedBy);
    return;
  }
  const item = orderItems.find((i) => i.id === id && i.served_by === servedBy);
  if (item) {
    item.qty = qty;
  }
  renderOrderSummary();
  updateGrandTotal();
}

function removeItem(id, servedBy) {
  orderItems = orderItems.filter(
    (i) => !(i.id === id && i.served_by === servedBy)
  );
  renderOrderSummary();
  updateGrandTotal();
  populateServerFilterSelect();
}

/**********************************************
 * Calculations (Subtotal, Tax, Grand Total)
 **********************************************/
function updateGrandTotal() {
  // Sum of all items
  const subtotal = orderItems.reduce(
    (sum, item) => sum + item.qty * item.price,
    0
  );
  const taxInput = document.getElementById("tax").value;
  const taxPercentage = parseFloat(taxInput) || 0;
  const tax = (subtotal * taxPercentage) / 100;
  const grandTotal = subtotal + tax;

  document.getElementById("subtotal").innerText = subtotal.toFixed(2);
  document.getElementById("grandTotal").innerText = grandTotal.toFixed(2);
}

document.getElementById("tax").addEventListener("input", updateGrandTotal);

/**********************************************
 * Save (Create/Update) Order
 **********************************************/
function saveOrder() {
  const tableNumber = document.getElementById("tableNumber").value.trim();
  const notes = document.getElementById("notes").value.trim();
  const taxValue = parseFloat(document.getElementById("tax").value) || 0;

  if (!tableNumber) {
    showMessage("Please enter the table number.", "error", true);
    return;
  }
  if (orderItems.length === 0) {
    showMessage("Please add at least one item to the order.", "error", true);
    return;
  }
  if (taxValue < 0) {
    showMessage("Please enter a valid tax percentage.", "error", true);
    return;
  }

  const data = {
    order_id: document.getElementById("orderId").value,
    table_number: tableNumber,
    notes: notes,
    items: orderItems, // array with 'qty' for each item
    subtotal: parseFloat(document.getElementById("subtotal").innerText),
    tax: taxValue,
    grand_total: parseFloat(document.getElementById("grandTotal").innerText),
  };

  fetch("/order/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
    .then((response) => {
      if (response.ok) {
        showMessage("Order saved successfully.", "success", true);
        setTimeout(() => {
          location.reload();
        }, 1000);
      } else {
        return response.json().then((respData) => {
          throw new Error(respData.message || "Error saving the order.");
        });
      }
    })
    .catch((error) => {
      showMessage(error.message, "error", true);
    });
}

/**********************************************
 * Partial Payment Modal
 **********************************************/
function openPaymentModal(orderId, remaining) {
  document.getElementById("paymentOrderId").value = orderId;
  document.getElementById("paymentAmount").value = "";
  document.getElementById("paymentRemaining").innerText =
    parseFloat(remaining).toFixed(2);

  document.getElementById("paymentModal").classList.remove("hidden");
}

function closePaymentModal() {
  document.getElementById("paymentModal").classList.add("hidden");
}

function submitPayment() {
  const orderId = document.getElementById("paymentOrderId").value;
  const paymentAmountInput = document.getElementById("paymentAmount").value;
  const paymentAmount = parseFloat(paymentAmountInput);

  if (isNaN(paymentAmount) || paymentAmount <= 0) {
    showPaymentMessage("Please enter a valid payment amount.", "error");
    return;
  }

  fetch(`/order/pay/${orderId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_amount: paymentAmount }),
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      } else {
        return response.json().then((data) => {
          throw new Error(data.message || "Payment error.");
        });
      }
    })
    .then((data) => {
      showMessage("Payment processed successfully.", "success");
      setTimeout(() => {
        location.reload();
      }, 1000);
    })
    .catch((error) => {
      showPaymentMessage(error.message, "error");
    });
}

function showPaymentMessage(message, type = "success") {
  const msgEl = document.getElementById("paymentModalMessage");
  msgEl.innerText = message;
  msgEl.classList.remove(
    "hidden",
    "bg-green-100",
    "bg-red-100",
    "text-green-700",
    "text-red-700"
  );

  if (type === "success") {
    msgEl.classList.add("bg-green-100", "text-green-700");
  } else {
    msgEl.classList.add("bg-red-100", "text-red-700");
  }
}

/**********************************************
 * Settle (Toggle Paid/Unpaid), Delete, Clear
 **********************************************/
function settleOrder(orderId) {
  fetch(`/order/settle/${orderId}`, { method: "POST" })
    .then((response) => {
      if (response.ok) {
        showMessage("Order status updated successfully.", "success");
        setTimeout(() => {
          location.reload();
        }, 1000);
      } else {
        return response.json().then((data) => {
          throw new Error(data.message || "Error updating order status.");
        });
      }
    })
    .catch((error) => {
      showMessage(error.message, "error");
    });
}

function deleteOrder(orderId) {
  if (confirm("Are you sure you want to delete this order?")) {
    fetch(`/order/delete/${orderId}`, { method: "POST" })
      .then((response) => {
        if (response.ok) {
          showMessage("Order deleted successfully.", "success");
          setTimeout(() => {
            location.reload();
          }, 1000);
        } else {
          return response.json().then((data) => {
            throw new Error(data.message || "Cannot delete unpaid orders.");
          });
        }
      })
      .catch((error) => {
        showMessage(error.message, "error");
      });
  }
}

function clearAllOrders() {
  if (confirm("Are you sure you want to delete all paid orders?")) {
    fetch("/orders/clear", { method: "POST" })
      .then((response) => {
        if (response.ok) {
          showMessage("All paid orders have been deleted.", "success");
          setTimeout(() => {
            location.reload();
          }, 1000);
        } else {
          return response.json().then((data) => {
            throw new Error(data.message || "Error clearing paid orders.");
          });
        }
      })
      .catch((error) => {
        showMessage(error.message, "error");
      });
  }
}

/**********************************************
 * Toggle Paid Orders Section
 **********************************************/
function togglePaidOrders() {
  const section = document.getElementById("paidOrdersSection");
  const icon = document.getElementById("paidOrdersIcon");
  section.classList.toggle("hidden");
  icon.classList.toggle("transform");
  icon.classList.toggle("rotate-180");
}

/**********************************************
 * Show Message Helper
 **********************************************/
function showMessage(message, type = "success", inModal = false) {
  const messageArea = inModal
    ? document.getElementById("modalMessageArea")
    : document.getElementById("pageMessageArea");

  if (!messageArea) {
    console.error("Message area element not found.");
    return;
  }

  messageArea.innerText = message;
  messageArea.classList.remove(
    "hidden",
    "bg-green-100",
    "bg-red-100",
    "text-green-700",
    "text-red-700",
    "border-green-500",
    "border-red-500"
  );

  if (type === "success") {
    messageArea.classList.add(
      "bg-green-100",
      "text-green-700",
      "border",
      "border-green-500"
    );
  } else {
    messageArea.classList.add(
      "bg-red-100",
      "text-red-700",
      "border",
      "border-red-500"
    );
  }

  setTimeout(() => {
    messageArea.classList.add("hidden");
  }, 3000);
}

/**********************************************
 * Filter Menu Items
 **********************************************/
function filterMenuItems() {
  const searchQuery = document.getElementById("menuSearch").value.toLowerCase();
  const selectedCategory = document
    .getElementById("categoryFilter")
    .value.toLowerCase();

  const menuItemsContainer = document.getElementById("menuItemsContainer");
  const items = menuItemsContainer.getElementsByTagName("div");

  for (let i = 0; i < items.length; i++) {
    const itemName = items[i].querySelector("h4").innerText.toLowerCase();
    const itemCategory = items[i].getAttribute("data-category").toLowerCase();

    const matchesSearch = itemName.includes(searchQuery) || searchQuery === "";
    const matchesCategory =
      itemCategory === selectedCategory || selectedCategory === "";

    if (matchesSearch && matchesCategory) {
      items[i].classList.remove("hidden");
    } else {
      items[i].classList.add("hidden");
    }
  }
}

async function printBill(saleId) {
  try {
    const response = await fetch(`/get-sale/${saleId}`);
    if (!response.ok) {
      alert("Failed to fetch sale data. Please try again.");
      return;
    }
    const sale = await response.json();

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({
      unit: "mm",
      format: [80, 120 + sale.items.length * 10],
    });

    const pageWidth = doc.internal.pageSize.getWidth();
    const centerX = pageWidth / 2;
    let yPos = 10;

    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Podda Restaurant LLC", centerX, yPos, { align: "center" });

    yPos += 8;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Date: ${sale.date} ${sale.time}`, centerX, yPos, {
      align: "center",
    });

    yPos += 8;
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text(`Customer: ${sale.customer || "N/A"}`, 5, yPos);
    yPos += 5;
    doc.text(`Server: ${sale.server}`, 5, yPos);

    yPos += 10;
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text("Item", 5, yPos);
    doc.text("Qty", 38, yPos, { align: "right" });
    doc.text("Price", 55, yPos, { align: "right" });
    doc.text("Total", 75, yPos, { align: "right" });

    yPos += 5;
    doc.setFont("helvetica", "normal");
    sale.items.forEach((item) => {
      let lines = doc.splitTextToSize(item.name, 30);
      doc.text(lines, 5, yPos);
      doc.text(String(item.qty), 38, yPos, { align: "right" });
      doc.text(item.price.toFixed(2), 55, yPos, { align: "right" });
      doc.text((item.qty * item.price).toFixed(2), 75, yPos, {
        align: "right",
      });

      yPos += lines.length * 5;
    });

    yPos += 5;
    doc.setFont("helvetica", "bold");
    doc.line(5, yPos, 75, yPos);
    yPos += 5;
    doc.text(`Subtotal: ${sale.subtotal.toFixed(2)}`, 5, yPos);
    yPos += 5;
    doc.text(`Tax: ${sale.tax.toFixed(2)}`, 5, yPos);
    yPos += 5;
    doc.text(`Discount: ${sale.discount.toFixed(2)}`, 5, yPos);
    yPos += 5;
    doc.setFontSize(12);
    doc.setTextColor(255, 0, 0);
    doc.text(`Grand Total: ${sale.grand_total.toFixed(2)}`, 5, yPos);

    yPos += 10;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(40, 40, 40);
    doc.text("Thank you for dining with us!", centerX, yPos, {
      align: "center",
    });

    // Print in new window:
    doc.autoPrint();
    const printBlob = doc.output("bloburl");
    window.open(printBlob);

    // OR to download instead:
    // doc.save(`bill_${sale.invoice_number}.pdf`);
  } catch (err) {
    console.error(err);
    alert("Error occurred while printing the bill.");
  }
}
