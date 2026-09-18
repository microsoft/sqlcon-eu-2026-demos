using FictionalOps.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace FictionalOps.Web.Data;

public class OperationsDbContext(DbContextOptions<OperationsDbContext> options) : DbContext(options)
{
    public DbSet<Customer> Customers => Set<Customer>();
    public DbSet<Product> Products => Set<Product>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderItem> OrderItems => Set<OrderItem>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Customer>().HasIndex(customer => customer.Email).IsUnique();
        modelBuilder.Entity<Product>().HasIndex(product => product.Sku).IsUnique();
        modelBuilder.Entity<Product>().Property(product => product.UnitPrice).HasPrecision(12, 2);
        modelBuilder.Entity<Order>().Property(order => order.TotalAmount).HasPrecision(12, 2);
        modelBuilder.Entity<OrderItem>().Property(item => item.UnitPrice).HasPrecision(12, 2);
        modelBuilder.Entity<OrderItem>().HasIndex(item => new { item.OrderId, item.ProductId }).IsUnique();
    }
}