using FictionalOps.Web.Data;
using FictionalOps.Web.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace FictionalOps.Web.Controllers;

public class InventoryController(OperationsDbContext database) : Controller
{
    public async Task<IActionResult> Index()
    {
        var productData = await database.Products.AsNoTracking()
            .Include(product => product.OrderItems)
            .ThenInclude(item => item.Order)
            .ToListAsync();
        var products = productData
            .Select(product => new InventoryItemViewModel(
                product,
                product.OrderItems.Where(item => item.Order.Status != "Fulfilled").Sum(item => item.Quantity),
                product.StockQuantity < 230 ? "Critical" : product.StockQuantity < 260 ? "Watch" : "Healthy"))
            .OrderBy(item => item.Product.StockQuantity)
            .ToList();
        return View(products);
    }
}