using FictionalOps.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace FictionalOps.Web.Data;

public static class SeedData
{
    public static async Task InitializeAsync(IServiceProvider services)
    {
        await using var scope = services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<OperationsDbContext>();
        await database.Database.EnsureCreatedAsync();

        var productNames = new[]
        {
            "Reinforced Shipping Cartons", "Biodegradable Packing Peanuts", "Industrial Stretch Wrap",
            "Tamper-Evident Security Tape", "Thermal Shipping Labels", "Padded Mailer Envelopes",
            "Reusable Plastic Totes", "Heavy-Duty Storage Bins", "Warehouse Pallet Covers",
            "Adjustable Cargo Straps", "Shock Indicator Labels", "Moisture Barrier Bags",
            "Insulated Shipping Liners", "Cold Chain Gel Packs", "Corrugated Divider Sets",
            "Anti-Static Bubble Wrap", "Edge Protector Boards", "Reusable Pallet Bands",
            "Document Enclosed Pouches", "Inventory Barcode Labels", "Warehouse Safety Markers",
            "Protective Foam Sheets", "Steel Strapping Coils", "Portable Shipping Scale"
        };

        if (await database.Customers.AnyAsync())
        {
            var replacementNames = productNames.Select((name, index) => new { Sku = $"FOP-{index + 1:000}", Name = name })
                .ToDictionary(product => product.Sku, product => product.Name);
            var legacyProducts = await database.Products
                .Where(product => product.Name.StartsWith("Operations Supply "))
                .ToListAsync();

            foreach (var product in legacyProducts)
            {
                if (replacementNames.TryGetValue(product.Sku, out var replacementName)) product.Name = replacementName;
            }

            if (legacyProducts.Count > 0) await database.SaveChangesAsync();
            return;
        }

        var partnerNames = new[]
        {
            "Northstar Mercantile", "Brass Lantern Goods", "Tideglass Supply", "Juniper Works",
            "Cinder & Coast", "Atlas Orchard", "Copper Kite Trading", "Blue Heron Outfitters",
            "Pinewake Provisioners", "Beacon Row Market", "Sunward Foundry", "Morrow Field Co.",
            "Cloudbreak Hardware", "Red Sail Collective", "Wren & Wharf", "Silver Current Labs",
            "Mariner's Table", "Emberline Equipment"
        };
        var regions = new[] { "Northeast", "Southeast", "Midwest", "Southwest", "Pacific" };
        var customers = partnerNames.Select((name, index) => new Customer
        {
            Name = name,
            Email = $"dispatch{index + 1:00}@example.test",
            Region = regions[index % regions.Length]
        }).ToList();
        var products = Enumerable.Range(1, 24).Select(index => new Product
        {
            Sku = $"FOP-{index:000}",
            Name = productNames[index - 1],
            UnitPrice = 12.50m + (index * 3.75m),
            StockQuantity = 200 + (index * 10)
        }).ToList();

        database.AddRange(customers);
        database.AddRange(products);
        await database.SaveChangesAsync();

        var orders = Enumerable.Range(1, 60).Select(index => new Order
        {
            CustomerId = customers[(index - 1) % customers.Count].Id,
            OrderedAtUtc = DateTime.UtcNow.Date.AddDays(-index),
            Status = index % 5 == 0 ? "Fulfilled" : index % 3 == 0 ? "Processing" : "Submitted",
            Notes = index % 7 == 0 ? "Priority warehouse handling" : null
        }).ToList();
        database.Orders.AddRange(orders);
        await database.SaveChangesAsync();

        foreach (var order in orders)
        {
            var firstProduct = products[(order.Id - 1) % products.Count];
            var secondProduct = products[(order.Id + 6) % products.Count];
            order.Items =
            [
                new OrderItem { ProductId = firstProduct.Id, Quantity = 1 + order.Id % 4, UnitPrice = firstProduct.UnitPrice },
                new OrderItem { ProductId = secondProduct.Id, Quantity = 1 + order.Id % 2, UnitPrice = secondProduct.UnitPrice }
            ];
            order.TotalAmount = order.Items.Sum(item => item.Quantity * item.UnitPrice);
        }

        await database.SaveChangesAsync();
    }
}