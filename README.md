# Cymbal Shops E-commerce Agents

An AI-powered e-commerce assistant system built for the GKE Turns 10 Hackathon. This project enhances the Cymbal Shops online boutique with intelligent agent capabilities using Google's Agent Development Kit (ADK).

## 🏗️ Architecture

The system consists of five specialized agents orchestrated by a main coordinator:

```mermaid
graph TB
    %% User Interface
    User[👤 User] --> UI[🖥️ ADK Web Interface]
    UI --> Runner[🚀 ADK Runner]

    %% Main Coordinator
    Runner --> RootAgent[🏪 Ecommerce Root Agent]

    %% Specialized Agents
    RootAgent --> ProductFinder[🔍 Product Finder<br/>Search & Details]
    RootAgent --> ProductRec[💡 Recommendations<br/>Browse & Suggest]
    RootAgent --> OrderAgent[🛒 Order Management<br/>Cart & Checkout]
    RootAgent --> VirtualTryon[✨ Virtual Try-On<br/>AI Image Generation]
    RootAgent --> ExportAgent[📄 Export Data<br/>PDF Generation]

    %% External Services
    ProductFinder --> CymbalShops[🏪 Cymbal Shops Website]
    ProductRec --> CymbalShops
    VirtualTryon --> AIServices[🤖 AI Image Services]
    ExportAgent --> PDFLib[📊 PDF Libraries]

    %% Data Storage
    Runner --> Storage[📁 Data Storage<br/>Artifacts & Sessions]
    OrderAgent --> Storage
    VirtualTryon --> Storage
    ExportAgent --> Storage

    %% Styling
    classDef agentClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef serviceClass fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef externalClass fill:#fff3e0,stroke:#e65100,stroke-width:2px

    class RootAgent,ProductFinder,ProductRec,OrderAgent,VirtualTryon,ExportAgent agentClass
    class Runner,UI,Storage serviceClass
    class User,CymbalShops,AIServices,PDFLib externalClass
```

### Architecture Overview

The system follows a **hierarchical agent architecture** with specialized agents for different e-commerce functions:

### 🔍 Product Finder Agent
- **Purpose**: Search and discover products on the Cymbal Shops website
- **Features**:
  - Real-time product search using web scraping
  - Product detail retrieval with pricing and descriptions
  - MCP integration for external data sources
- **Tools**: `search_products()`, `get_product_details()`

### 💡 Product Recommendation Agent
- **Purpose**: Provide personalized product recommendations
- **Features**:
  - Category-based recommendations
  - Complementary product suggestions
  - Popular item recommendations
  - Style and preference-based filtering
- **Tools**: `get_all_products()`, `recommend_products()`

### 🛒 Order Placement Agent
- **Purpose**: Manage shopping cart and order processing
- **Features**:
  - Add/remove items from cart
  - Cart summary and total calculation
  - Simulated checkout process
  - Order confirmation and tracking
- **Tools**: `add_to_cart()`, `remove_from_cart()`, `view_cart()`, `simulate_checkout()`

### ✨ Virtual Try-On Agent
- **Purpose**: Enable virtual product try-on using AI image generation
- **Features**:
  - Image processing and validation
  - AI-powered virtual try-on (integration ready for nano banano API)
  - Style recommendations
  - Product suitability assessment
- **Tools**: `process_user_image()`, `generate_tryon_image()`, `get_style_recommendations()`

### 📄 Export Data Agent
- **Purpose**: Export order data and generate professional PDF documents
- **Features**:
  - Order confirmation PDF generation
  - Product details with pricing and quantities
  - Shipping and payment information
  - Professional formatting with tables and styling
  - Artifact storage for download
- **Tools**: `export_order_to_pdf()`, `validate_order_data()`, `get_order_from_placement_agent()`

## 🛠️ Technical Details

### Technologies Used
- **Google ADK 1.0.0**: Agent orchestration framework
- **FastAPI**: Web framework
- **BeautifulSoup4**: Web scraping
- **Pillow**: Image processing
- **MCP**: Model Context Protocol integration

### Data Sources
- **Primary**: Cymbal Shops website (https://cymbal-shops.retail.cymbal.dev/)
- **Product Data**: Real-time scraping from the live demo site
- **Cart Storage**: In-memory (production would use database)

### AI Models
- **LLM**: Gemini 2.0 Flash for agent reasoning and orchestration
- **Image Generation**: Gemini 2.5 Flash Image Preview for virtual try-on

## 🚀 Deployment

### Local Development
```bash
python3 -m venv venv
source venv/bin/activate

cp ecommerce_agent/.env.example ecommerce_agent/.env

## Update the ecommerce_agent/.env with API keys

pip install -r ecommerce_agent/requirements.txt
adk web ecommerce_agent

## Open url: http://127.0.0.1:8000
```

### Production (GKE)
1. Build Docker container
2. Deploy to Google Kubernetes Engine
3. Configure secrets and environment variables
4. Set up load balancing and scaling

## 📊 Performance

### Agent Response Times
- **Product Search**: ~1-2 seconds
- **Recommendations**: ~1-3 seconds
- **Cart Operations**: ~0.5 seconds
- **Virtual Try-On**: ~2-5 seconds
- **PDF Export**: ~1-2 seconds

## 📋 Sample Outputs

### Export Data Agent
The Export Data Agent generates professional PDF documents for order confirmations. A sample output is available:

📄 **[Sample Order PDF](./sample_exported_order_pdf.pdf)** - Demonstrates the PDF export functionality with:
- Order confirmation details and tracking information
- Complete product listings with prices and quantities
- Shipping address and payment method information
- Professional formatting with tables and branding
- Total cost calculations and order summary

## 📜 License

Built for educational and hackathon purposes. See the original Cymbal Shops license for base application terms.

---

*Built with ❤️ for the GKE Hackathon 2025*