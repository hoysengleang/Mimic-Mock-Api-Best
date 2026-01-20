

using LiteDB;
var builder = WebApplication.CreateBuilder(args);


builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// src/Mimic.API/Program.cs

var dbConnectionString = builder.Configuration.GetConnectionString("LiteDB") 
             ?? "Filename=/app/data/Mimic.db;Connection=Shared";

builder.Services.AddSingleton<ILiteDatabase>(_ => 
{
    // EXTRACT PATH: Parse the filename from the connection string
    // This is a simple hack to get "/app/data/Mimic.db"
    var path = dbConnectionString.Split(';')
                .FirstOrDefault(x => x.StartsWith("Filename="))?
                .Replace("Filename=", "") ?? "";

    if (!string.IsNullOrEmpty(path))
    {
        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
        {
            // Auto-create the directory if it's missing
            Directory.CreateDirectory(directory);
            Console.WriteLine($"[Mimic] Created database directory: {directory}");
        }
    }

    var db = new LiteDatabase(dbConnectionString);
    
    // Performance Indexing
    var col = db.GetCollection<MockDefinition>("mocks");
    col.EnsureIndex(x => x.Path);
    col.EnsureIndex(x => x.Method);
    
    return db;
});

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
