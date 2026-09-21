using System.Diagnostics;
using FictionalOps.Web.Data;
using Microsoft.AspNetCore.Mvc;
using FictionalOps.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace FictionalOps.Web.Controllers;

public class HomeController(OperationsDbContext database, ILogger<HomeController> logger) : Controller
{
    public async Task<IActionResult> Index()
    {
        logger.LogDebug("Loading operations dashboard");
        var totalOrders = await database.Orders.CountAsync();
        var fulfilledOrders = await database.Orders.CountAsync(order => order.Status == "Fulfilled");
        var revenue = await database.Orders.SumAsync(order => order.TotalAmount);
        var customers = await database.Customers.AsNoTracking().Include(customer => customer.Orders).ToListAsync();
        var topPartners = customers
            .Select(customer => new PartnerPerformanceViewModel(
                customer.Id,
                customer.Name,
                customer.Region,
                customer.Orders.Count,
                customer.Orders.Count(order => order.Status != "Fulfilled"),
                customer.Orders.Sum(order => order.TotalAmount),
                customer.Orders.Max(order => (DateTime?)order.OrderedAtUtc)))
            .OrderByDescending(partner => partner.LifetimeValue)
            .Take(5)
            .ToList();
        var model = new DashboardViewModel(
            await database.Orders.CountAsync(order => order.Status != "Fulfilled"),
            await database.Orders.CountAsync(order => order.Status != "Fulfilled" && order.OrderedAtUtc < DateTime.UtcNow.AddDays(-5)),
            await database.Products.CountAsync(product => product.IsActive && product.StockQuantity < 260),
            revenue,
            totalOrders == 0 ? 0 : revenue / totalOrders,
            totalOrders == 0 ? 0 : (int)Math.Round(fulfilledOrders * 100m / totalOrders),
            await database.Orders.Include(order => order.Customer).OrderByDescending(order => order.OrderedAtUtc).Take(6).ToListAsync(),
            await database.Products.Where(product => product.IsActive && product.StockQuantity < 260).OrderBy(product => product.StockQuantity).Take(5).ToListAsync(),
            topPartners);
        return View(model);
    }

    public IActionResult Privacy()
    {
        return View();
    }

    [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
    public IActionResult Error()
    {
        return View(new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier });
    }
}
