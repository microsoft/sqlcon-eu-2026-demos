using FictionalOps.Web.Data;
using FictionalOps.Web.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace FictionalOps.Web.Controllers;

public class PartnersController(OperationsDbContext database) : Controller
{
    public async Task<IActionResult> Index()
    {
        var customers = await database.Customers.AsNoTracking().Include(customer => customer.Orders).ToListAsync();
        var partners = customers
            .Select(customer => new PartnerPerformanceViewModel(
                customer.Id,
                customer.Name,
                customer.Region,
                customer.Orders.Count,
                customer.Orders.Count(order => order.Status != "Fulfilled"),
                customer.Orders.Sum(order => order.TotalAmount),
                customer.Orders.Max(order => (DateTime?)order.OrderedAtUtc)))
            .OrderByDescending(partner => partner.LifetimeValue)
            .ToList();
        return View(partners);
    }

    public async Task<IActionResult> Details(int id)
    {
        var customer = await database.Customers.AsNoTracking().SingleOrDefaultAsync(entity => entity.Id == id);
        if (customer is null) return NotFound();
        var orders = await database.Orders.AsNoTracking().Where(order => order.CustomerId == id).OrderByDescending(order => order.OrderedAtUtc).ToListAsync();
        var lifetimeValue = orders.Sum(order => order.TotalAmount);
        return View(new PartnerDetailsViewModel(customer, orders, lifetimeValue, orders.Count == 0 ? 0 : lifetimeValue / orders.Count));
    }
}