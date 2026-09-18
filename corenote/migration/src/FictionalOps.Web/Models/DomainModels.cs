using System.ComponentModel.DataAnnotations;

namespace FictionalOps.Web.Models;

public class Customer
{
    public int Id { get; set; }
    [Required, StringLength(120)] public string Name { get; set; } = string.Empty;
    [Required, EmailAddress, StringLength(160)] public string Email { get; set; } = string.Empty;
    [StringLength(80)] public string Region { get; set; } = string.Empty;
    public bool IsActive { get; set; } = true;
    public ICollection<Order> Orders { get; set; } = [];
}

public class Product
{
    public int Id { get; set; }
    [Required, StringLength(30)] public string Sku { get; set; } = string.Empty;
    [Required, StringLength(140)] public string Name { get; set; } = string.Empty;
    public decimal UnitPrice { get; set; }
    public int StockQuantity { get; set; }
    public bool IsActive { get; set; } = true;
    public ICollection<OrderItem> OrderItems { get; set; } = [];
}

public class Order
{
    public int Id { get; set; }
    public int CustomerId { get; set; }
    public Customer Customer { get; set; } = null!;
    public DateTime OrderedAtUtc { get; set; }
    [Required, StringLength(30)] public string Status { get; set; } = "Submitted";
    public decimal TotalAmount { get; set; }
    [StringLength(240)] public string? Notes { get; set; }
    public ICollection<OrderItem> Items { get; set; } = [];
}

public class OrderItem
{
    public int Id { get; set; }
    public int OrderId { get; set; }
    public Order Order { get; set; } = null!;
    public int ProductId { get; set; }
    public Product Product { get; set; } = null!;
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
}