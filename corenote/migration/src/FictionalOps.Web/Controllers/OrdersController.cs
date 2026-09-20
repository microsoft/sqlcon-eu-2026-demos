using FictionalOps.Web.Data;
using FictionalOps.Web.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering;
using Microsoft.EntityFrameworkCore;

namespace FictionalOps.Web.Controllers;

public class OrdersController(OperationsDbContext database) : Controller
{
    public async Task<IActionResult> Index(string? status)
    {
        var query = database.Orders.Include(order => order.Customer).AsNoTracking();
        if (!string.IsNullOrWhiteSpace(status)) query = query.Where(order => order.Status == status);
        ViewBag.Status = status;
        return View(await query.OrderByDescending(order => order.OrderedAtUtc).ToListAsync());
    }

    public async Task<IActionResult> Details(int id)
    {
        var order = await database.Orders.AsNoTracking()
            .Include(entity => entity.Customer)
            .Include(entity => entity.Items).ThenInclude(item => item.Product)
            .SingleOrDefaultAsync(entity => entity.Id == id);
        return order is null ? NotFound() : View(order);
    }

    public async Task<IActionResult> Fulfillment()
    {
        return View(await database.Orders.AsNoTracking()
            .Include(order => order.Customer)
            .Where(order => order.Status != "Fulfilled")
            .OrderBy(order => order.Status == "Processing" ? 0 : 1)
            .ThenBy(order => order.OrderedAtUtc)
            .ToListAsync());
    }

    [HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> AdvanceStatus(int id)
    {
        var order = await database.Orders.FindAsync(id);
        if (order is null) return NotFound();

        order.Status = order.Status switch
        {
            "Submitted" => "Processing",
            "Processing" => "Fulfilled",
            _ => order.Status
        };
        await database.SaveChangesAsync();
        TempData["Message"] = $"Order #{order.Id} advanced to {order.Status}.";
        return RedirectToAction(nameof(Fulfillment));
    }

    public async Task<IActionResult> Create() => View(await PopulateSelectionsAsync(new CreateOrderViewModel()));

    [HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> Create(CreateOrderViewModel model)
    {
        var product = await database.Products.SingleOrDefaultAsync(entity => entity.Id == model.ProductId && entity.IsActive);
        if (product is null) ModelState.AddModelError(nameof(model.ProductId), "The selected product is unavailable.");
        else if (product.StockQuantity < model.Quantity) ModelState.AddModelError(nameof(model.Quantity), "Not enough stock is available.");
        if (!await database.Customers.AnyAsync(entity => entity.Id == model.CustomerId && entity.IsActive))
            ModelState.AddModelError(nameof(model.CustomerId), "The selected customer is unavailable.");

        if (!ModelState.IsValid) return View(await PopulateSelectionsAsync(model));

        var order = new Order
        {
            CustomerId = model.CustomerId,
            OrderedAtUtc = DateTime.UtcNow,
            Status = "Submitted",
            Notes = model.Notes,
            TotalAmount = product!.UnitPrice * model.Quantity,
            Items = [new OrderItem { ProductId = product.Id, Quantity = model.Quantity, UnitPrice = product.UnitPrice }]
        };
        product.StockQuantity -= model.Quantity;
        database.Orders.Add(order);
        await database.SaveChangesAsync();
        TempData["Message"] = $"Order #{order.Id} was submitted.";
        return RedirectToAction(nameof(Details), new { id = order.Id });
    }

    private async Task<CreateOrderViewModel> PopulateSelectionsAsync(CreateOrderViewModel model)
    {
        model.Customers = await database.Customers.Where(entity => entity.IsActive).OrderBy(entity => entity.Name)
            .Select(entity => new SelectListItem(entity.Name, entity.Id.ToString())).ToListAsync();
        model.Products = await database.Products.Where(entity => entity.IsActive).OrderBy(entity => entity.Name)
            .Select(entity => new SelectListItem($"{entity.Name} ({entity.StockQuantity} available) - {entity.UnitPrice:C}", entity.Id.ToString())).ToListAsync();
        return model;
    }
}