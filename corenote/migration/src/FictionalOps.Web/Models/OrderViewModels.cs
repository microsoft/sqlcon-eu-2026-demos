using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Mvc.Rendering;

namespace FictionalOps.Web.Models;

public class CreateOrderViewModel
{
    [Range(1, int.MaxValue, ErrorMessage = "Select a customer.")]
    public int CustomerId { get; set; }

    [Range(1, int.MaxValue, ErrorMessage = "Select a product.")]
    public int ProductId { get; set; }

    [Range(1, 25)] public int Quantity { get; set; } = 1;
    [StringLength(240)] public string? Notes { get; set; }
    public IReadOnlyList<SelectListItem> Customers { get; set; } = [];
    public IReadOnlyList<SelectListItem> Products { get; set; } = [];
}

public record DashboardViewModel(
    int OpenOrders,
    int OrdersAtRisk,
    int LowStockProducts,
    decimal Revenue,
    decimal AverageOrderValue,
    int FulfillmentRate,
    IReadOnlyList<Order> RecentOrders,
    IReadOnlyList<Product> StockRisks,
    IReadOnlyList<PartnerPerformanceViewModel> TopPartners);

public record InventoryItemViewModel(Product Product, int UnitsCommitted, string RiskLevel);

public record PartnerPerformanceViewModel(
    int CustomerId,
    string Name,
    string Region,
    int OrderCount,
    int OpenOrders,
    decimal LifetimeValue,
    DateTime? LastOrderUtc);

public record PartnerDetailsViewModel(Customer Customer, IReadOnlyList<Order> Orders, decimal LifetimeValue, decimal AverageOrderValue);